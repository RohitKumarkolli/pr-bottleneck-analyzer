import sqlite3
from datetime import datetime, timezone

from src.ingestion.db import SCHEMA
from src.metrics.compute import compute_pr

def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

def add_pr(conn, n, created, state="open", merged=None, draft=0, author="alice"):
    conn.execute(
        "INSERT INTO prs (repo, number, title, author, author_is_bot, state, draft, "
        "created_at, updated_at, closed_at, merged_at, raw_json, ingested_at) "
        "VALUES ('r',?,'t',?,0,?,?,?,?,?,?,'{}','x')",
        (n, author, state, draft, created, created, merged, merged))

def add_comment(conn, n, cid, author, ts, kind="issue_comment", bot=0):
    conn.execute(
        "INSERT INTO comments (repo, kind, id, pr_number, author, author_is_bot, "
        "created_at, body, review_state, raw_json) VALUES ('r',?,?,?,?,?,?,'x',NULL,'{}')",
        (kind, cid, n, author, bot, ts))

def add_commit(conn, n, sha, author, ts):
    conn.execute(
        "INSERT INTO commits (repo, sha, pr_number, author, committed_at, raw_json) "
        "VALUES ('r',?,?,?,?,'{}')", (sha, n, author, ts))

def run(conn, n, now):
    pr = conn.execute("SELECT * FROM prs WHERE number=?", (n,)).fetchone()
    return compute_pr(conn, pr, now, stall_days=7)

NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)

def test_open_pr_waiting_on_reviewer():
    c = make_conn()
    add_pr(c, 1, "2026-09-01T00:00:00Z")
    add_comment(c, 1, 1, "bob", "2026-09-02T00:00:00Z")   # reviewer responds after 24h
    add_commit(c, 1, "a", "alice", "2026-09-03T00:00:00Z")  # author pushes a fix
    m = run(c, 1, NOW)
    assert m["ttfr_hours"] == 24
    assert m["waiting_on"] == "reviewer"        # last actor was the author
    assert m["idle_hours"] == 192               # 8 days since the commit
    assert m["is_stalled"] == 1

def test_bot_comments_are_ignored():
    c = make_conn()
    add_pr(c, 2, "2026-09-08T00:00:00Z")
    add_comment(c, 2, 1, "ci-bot[bot]", "2026-09-09T00:00:00Z", bot=1)
    m = run(c, 2, NOW)
    assert m["ttfr_hours"] is None
    assert m["idle_hours"] == 72                # measured from creation, not the bot
    assert m["is_stalled"] == 0

def test_merged_pr_ttm():
    c = make_conn()
    add_pr(c, 3, "2026-09-01T00:00:00Z", state="closed", merged="2026-09-04T12:00:00Z")
    m = run(c, 3, NOW)
    assert m["ttm_hours"] == 84
    assert m["idle_hours"] is None