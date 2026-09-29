import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.db import get_conn

n = int(sys.argv[1])
conn = get_conn()
pr = conn.execute("SELECT number, title, author, state, draft, created_at, merged_at FROM prs WHERE number=?", (n,)).fetchone()
print(dict(pr))

events = []
for c in conn.execute("SELECT created_at, author, kind, author_is_bot FROM comments WHERE pr_number=?", (n,)):
    events.append((c["created_at"], c["author"], c["kind"] + (" [BOT]" if c["author_is_bot"] else "")))
for c in conn.execute("SELECT committed_at, author, 'commit' FROM commits WHERE pr_number=?", (n,)):
    events.append(tuple(c))
print("\nTimeline:")
for e in sorted(events, key=lambda e: e[0] or ""):
    print(" ", e)

print("\nMetrics:")
print(dict(conn.execute("SELECT * FROM pr_metrics WHERE number=?", (n,)).fetchone()))