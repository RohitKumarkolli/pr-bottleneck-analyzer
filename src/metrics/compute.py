import statistics
from datetime import datetime, timezone

from src.config import TARGET_REPO, STALL_DAYS
from src.ingestion.db import get_conn

METRICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS pr_metrics (
    repo                 TEXT NOT NULL,
    number               INTEGER NOT NULL,
    state                TEXT,
    draft                INTEGER,
    author               TEXT,
    created_at           TEXT,
    first_response_at    TEXT,
    ttfr_hours           REAL,     -- NULL = no response yet
    merged_at            TEXT,
    ttm_hours            REAL,     -- NULL unless merged
    last_activity_at     TEXT,
    last_activity_actor  TEXT,
    idle_hours           REAL,     -- open PRs only
    waiting_on           TEXT,     -- 'author' | 'reviewer' (open PRs only)
    is_stalled           INTEGER,
    human_comment_count  INTEGER,
    commit_count         INTEGER,
    computed_at          TEXT,
    PRIMARY KEY (repo, number)
);
"""


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def hours(a, b):
    return (b - a).total_seconds() / 3600


def compute_pr(conn, pr, now, stall_days=STALL_DAYS):
    repo, n, author = pr["repo"], pr["number"], pr["author"]
    created = parse(pr["created_at"])

    # Build a single timeline of human events: (time, actor, kind)
    events = []
    comment_count = 0
    for c in conn.execute(
        "SELECT created_at, author, kind FROM comments "
        "WHERE repo=? AND pr_number=? AND author_is_bot=0", (repo, n)):
        events.append((parse(c["created_at"]), c["author"], c["kind"]))
        comment_count += 1

    commit_count = 0
    for c in conn.execute(
        "SELECT committed_at, author FROM commits WHERE repo=? AND pr_number=?",
        (repo, n)):
        commit_count += 1
        if not c["committed_at"]:
            continue
        t = parse(c["committed_at"])
        if t < created:
            continue  # commits authored before the PR opened aren't "activity on the PR"
        # Unlinked git emails give author=None; attribute to the PR author
        events.append((t, c["author"] or author, "commit"))

    events.sort(key=lambda e: e[0])

    # TTFR: first non-author, non-commit human event
    first_resp = next((e for e in events if e[1] != author and e[2] != "commit"), None)

    m = {
        "repo": repo, "number": n, "state": pr["state"], "draft": pr["draft"],
        "author": author, "created_at": pr["created_at"],
        "first_response_at": first_resp[0].isoformat() if first_resp else None,
        "ttfr_hours": hours(created, first_resp[0]) if first_resp else None,
        "merged_at": pr["merged_at"],
        "ttm_hours": hours(created, parse(pr["merged_at"])) if pr["merged_at"] else None,
        "last_activity_at": None, "last_activity_actor": None,
        "idle_hours": None, "waiting_on": None, "is_stalled": 0,
        "human_comment_count": comment_count, "commit_count": commit_count,
        "computed_at": now.isoformat(),
    }

    if pr["state"] == "open":
        last_t, last_actor = (events[-1][0], events[-1][1]) if events else (created, author)
        m["last_activity_at"] = last_t.isoformat()
        m["last_activity_actor"] = last_actor
        m["idle_hours"] = hours(last_t, now)
        m["waiting_on"] = "reviewer" if last_actor == author else "author"
        m["is_stalled"] = int(not pr["draft"] and m["idle_hours"] > stall_days * 24)
    return m


def compute_all(repo=TARGET_REPO, now=None):
    now = now or datetime.now(timezone.utc)
    conn = get_conn()
    conn.executescript(METRICS_SCHEMA)

    rows = [compute_pr(conn, pr, now)
            for pr in conn.execute("SELECT * FROM prs WHERE repo=?", (repo,))]

    with conn:  # one transaction: delete + reinsert
        conn.execute("DELETE FROM pr_metrics WHERE repo=?", (repo,))
        for m in rows:
            cols = ", ".join(m)
            ph = ", ".join(f":{k}" for k in m)
            conn.execute(f"INSERT INTO pr_metrics ({cols}) VALUES ({ph})", m)
    return rows


def summarize(rows):
    def med(xs):
        return f"{statistics.median(xs):.1f}h" if xs else "n/a"

    open_prs = [r for r in rows if r["state"] == "open"]
    non_draft = [r for r in open_prs if not r["draft"]]
    print(f"PRs: {len(rows)} ({len(open_prs)} open)")
    print("Median TTFR :", med([r["ttfr_hours"] for r in rows if r["ttfr_hours"] is not None]))
    print("Median TTM  :", med([r["ttm_hours"] for r in rows if r["ttm_hours"] is not None]))
    no_resp = sum(r["ttfr_hours"] is None for r in rows)
    print(f"No response yet: {no_resp}/{len(rows)} ({100*no_resp/max(len(rows),1):.0f}%)")
    stalled = [r for r in non_draft if r["is_stalled"]]
    print(f"Stalled (> {STALL_DAYS}d idle, non-draft): {len(stalled)}/{len(non_draft)}")
    print("  waiting on reviewer:", sum(r["waiting_on"] == "reviewer" for r in stalled),
          "| on author:", sum(r["waiting_on"] == "author" for r in stalled))


if __name__ == "__main__":
    summarize(compute_all())