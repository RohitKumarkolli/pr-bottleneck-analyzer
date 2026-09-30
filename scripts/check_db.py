import sqlite3
import os
conn = sqlite3.connect("data/prs.db")

def show(title, query):
    print(f"\n--- {title} ---")
    for row in conn.execute(query):
        print(tuple(row))

show("PR count", "SELECT COUNT(*) FROM prs")
show("Commit count", "SELECT COUNT(*) FROM commits")
show("Comments by kind", "SELECT kind, COUNT(*) FROM comments GROUP BY kind")
show("PRs missing created_at (want 0)", "SELECT COUNT(*) FROM prs WHERE created_at IS NULL")
show("Comments missing created_at (want 0)", "SELECT COUNT(*) FROM comments WHERE created_at IS NULL")
show("State vs merged", "SELECT state, merged_at IS NOT NULL AS merged, COUNT(*) FROM prs GROUP BY 1,2")
show("Bot vs human comments (1 = bot)", "SELECT author_is_bot, COUNT(*) FROM comments GROUP BY 1")
show("Sample PR numbers", "SELECT number, title, state FROM prs LIMIT 5")

for row in conn.execute("SELECT number, primary_reason, blocker, idle_days FROM stuck_pr_reports ORDER BY idle_days DESC LIMIT 5;"):
    print(tuple(row))

# A PR with no human activity for this long (and not a draft) counts as stalled
STALL_DAYS = int(os.getenv("STALL_DAYS", "7"))