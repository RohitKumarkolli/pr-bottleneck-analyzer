import json
import time
from datetime import datetime, timedelta, timezone

from src.config import TARGET_REPO, LOOKBACK_DAYS, MAX_PRS_PER_STATE
from src.ingestion import github_client as gh
from src.ingestion.db import get_conn


def is_bot(user) -> int:
    if not user:
        return 0
    return int(user.get("type") == "Bot" or user.get("login", "").endswith("[bot]"))


def login(user):
    return user["login"] if user else None  # deleted accounts come back as null


def list_prs(repo):
    """Open PRs (all of them, up to cap) + closed PRs updated inside the lookback window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    prs = []

    n = 0
    for pr in gh.paginate(f"/repos/{repo}/pulls",
                          {"state": "open", "sort": "updated", "direction": "desc"}):
        prs.append(pr)
        n += 1
        if n >= MAX_PRS_PER_STATE:
            break

    n = 0
    for pr in gh.paginate(f"/repos/{repo}/pulls",
                          {"state": "closed", "sort": "updated", "direction": "desc"}):
        updated = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
        if updated < cutoff:
            break  # sorted desc, so everything after this is older
        prs.append(pr)
        n += 1
        if n >= MAX_PRS_PER_STATE:
            break
    return prs


def upsert_pr(conn, repo, pr):
    conn.execute(
        """INSERT OR REPLACE INTO prs
           (repo, number, title, author, author_is_bot, state, draft,
            created_at, updated_at, closed_at, merged_at, raw_json, ingested_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (repo, pr["number"], pr["title"], login(pr["user"]), is_bot(pr["user"]),
         pr["state"], int(pr.get("draft", False)),
         pr["created_at"], pr["updated_at"], pr["closed_at"], pr["merged_at"],
         json.dumps(pr), datetime.now(timezone.utc).isoformat()),
    )


def store_comments(conn, repo, number, kind, items):
    for c in items:
        # Reviews use submitted_at; comments use created_at
        ts = c.get("submitted_at") or c.get("created_at")
        conn.execute(
            """INSERT OR REPLACE INTO comments
               (repo, kind, id, pr_number, author, author_is_bot, created_at,
                body, review_state, raw_json)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (repo, kind, c["id"], number, login(c.get("user")), is_bot(c.get("user")),
             ts, c.get("body") or "", c.get("state") if kind == "review" else None,
             json.dumps(c)),
        )


def store_commits(conn, repo, number, items):
    for c in items:
        committer = (c["commit"].get("committer") or {})
        conn.execute(
            """INSERT OR REPLACE INTO commits
               (repo, sha, pr_number, author, committed_at, raw_json)
               VALUES (?,?,?,?,?,?)""",
            (repo, c["sha"], number, login(c.get("author")),
             committer.get("date"), json.dumps(c)),
        )


def ingest(repo=TARGET_REPO):
    t0 = time.time()
    conn = get_conn()

    print(f"Listing PRs for {repo}...")
    prs = list_prs(repo)
    print(f"Found {len(prs)} PRs (open + recently closed)")

    existing = {
        r["number"]: r["updated_at"]
        for r in conn.execute("SELECT number, updated_at FROM prs WHERE repo=?", (repo,))
    }

    fetched = skipped = 0
    for i, pr in enumerate(prs, 1):
        n = pr["number"]
        if existing.get(n) == pr["updated_at"]:
            skipped += 1
            continue

        try:
            reviews = list(gh.paginate(f"/repos/{repo}/pulls/{n}/reviews"))
            inline = list(gh.paginate(f"/repos/{repo}/pulls/{n}/comments"))
            issue = list(gh.paginate(f"/repos/{repo}/issues/{n}/comments"))
            commits = list(gh.paginate(f"/repos/{repo}/pulls/{n}/commits"))
        except Exception as e:
            # Don't write the PR row if enrichment failed, so the next run retries it
            print(f"  ! PR #{n} failed: {e}")
            continue

        upsert_pr(conn, repo, pr)
        store_comments(conn, repo, n, "review", reviews)
        store_comments(conn, repo, n, "review_comment", inline)
        store_comments(conn, repo, n, "issue_comment", issue)
        store_commits(conn, repo, n, commits)
        conn.commit()  # commit per PR: a crash mid-run loses at most one PR
        fetched += 1

        if i % 10 == 0:
            print(f"  {i}/{len(prs)} processed")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s | fetched {fetched}, skipped {skipped} unchanged "
          f"| API calls: {gh.api_calls}")


if __name__ == "__main__":
    ingest()