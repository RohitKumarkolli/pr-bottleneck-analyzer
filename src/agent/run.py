import json
import time
from datetime import datetime, timezone

from src.config import TARGET_REPO, REQUEST_DELAY
from src.ingestion.db import get_conn
from src.agent.graph import run_for_pr

SCHEMA = """
CREATE TABLE IF NOT EXISTS stuck_pr_reports (
    repo            TEXT NOT NULL,
    number          INTEGER NOT NULL,
    primary_reason  TEXT,
    explanation     TEXT,
    blocker         TEXT,
    nudge_message   TEXT,
    idle_days       REAL,
    generated_at    TEXT,
    PRIMARY KEY (repo, number)
);
"""


def run_all(repo=TARGET_REPO):
    conn = get_conn()
    conn.executescript(SCHEMA)
    stalled = conn.execute(
        "SELECT number, idle_hours FROM pr_metrics WHERE repo=? AND is_stalled=1 "
        "ORDER BY idle_hours DESC", (repo,)).fetchall()
    print(f"{len(stalled)} stalled PRs to analyze")

    for i, row in enumerate(stalled, 1):
        n = row["number"]
        try:
            result = run_for_pr(repo, n)
        except Exception as e:
            print(f"  ! PR #{n} failed: {e}")
            continue
        d, nudge = result["diagnosis"], result["nudge"]
        conn.execute(
            "INSERT OR REPLACE INTO stuck_pr_reports VALUES (?,?,?,?,?,?,?,?)",
            (repo, n, d.primary_reason, d.explanation, d.blocker, nudge.message,
             round(row["idle_hours"] / 24, 1), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        print(f"  [{i}/{len(stalled)}] PR #{n}: {d.primary_reason}")
        time.sleep(REQUEST_DELAY)


if __name__ == "__main__":
    run_all()