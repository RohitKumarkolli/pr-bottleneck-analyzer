import sqlite3
from src.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS prs (
    repo           TEXT NOT NULL,
    number         INTEGER NOT NULL,
    title          TEXT,
    author         TEXT,
    author_is_bot  INTEGER,
    state          TEXT,       -- 'open' | 'closed'
    draft          INTEGER,
    created_at     TEXT,
    updated_at     TEXT,
    closed_at      TEXT,
    merged_at      TEXT,
    raw_json       TEXT NOT NULL,
    ingested_at    TEXT NOT NULL,
    PRIMARY KEY (repo, number)
);

-- One table for all three comment sources; ID spaces differ so key includes kind
CREATE TABLE IF NOT EXISTS comments (
    repo           TEXT NOT NULL,
    kind           TEXT NOT NULL,   -- 'review_comment' | 'issue_comment' | 'review'
    id             INTEGER NOT NULL,
    pr_number      INTEGER NOT NULL,
    author         TEXT,
    author_is_bot  INTEGER,
    created_at     TEXT,
    body           TEXT,
    review_state   TEXT,            -- only for kind='review'
    raw_json       TEXT NOT NULL,
    PRIMARY KEY (repo, kind, id)
);

CREATE TABLE IF NOT EXISTS commits (
    repo           TEXT NOT NULL,
    sha            TEXT NOT NULL,
    pr_number      INTEGER NOT NULL,
    author         TEXT,
    committed_at   TEXT,
    raw_json       TEXT NOT NULL,
    PRIMARY KEY (repo, pr_number, sha)
);

CREATE INDEX IF NOT EXISTS idx_comments_pr ON comments (repo, pr_number);
CREATE INDEX IF NOT EXISTS idx_commits_pr  ON commits (repo, pr_number);
"""

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn