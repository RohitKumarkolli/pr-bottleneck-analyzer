from dataclasses import dataclass, field
from src.ingestion.db import get_conn
from src.config import TARGET_REPO


@dataclass
class PRContext:
    repo: str
    number: int
    title: str
    author: str
    idle_days: float
    waiting_on: str
    ttfr_hours: float | None
    human_comment_count: int
    category_counts: dict = field(default_factory=dict)
    sample_comments: list = field(default_factory=list)  # a few representative bodies, by category
    url: str = ""


def gather_context(repo: str, number: int) -> PRContext:
    conn = get_conn()
    pr = conn.execute(
        """SELECT m.*, p.title
           FROM pr_metrics m JOIN prs p ON p.repo=m.repo AND p.number=m.number
           WHERE m.repo=? AND m.number=?""", (repo, number)).fetchone()
    if pr is None:
        raise ValueError(f"No metrics for PR #{number}. Run compute.py first.")

    labels = conn.execute(
        """SELECT l.category, c.author, c.body
           FROM comment_labels l
           JOIN comments c ON c.repo=l.repo AND c.kind=l.kind AND c.id=l.id
           WHERE l.repo=? AND c.pr_number=?""",
        (repo, number)).fetchall()

    counts = {}
    samples = {}  # one representative comment per category, trimmed
    for row in labels:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
        if row["category"] not in samples and row["category"] != "other":
            samples[row["category"]] = f'{row["author"]}: "{row["body"][:200].strip()}"'

    return PRContext(
        repo=repo, number=number, title=pr["title"], author=pr["author"],
        idle_days=round(pr["idle_hours"] / 24, 1) if pr["idle_hours"] else 0,
        waiting_on=pr["waiting_on"],
        ttfr_hours=pr["ttfr_hours"],
        human_comment_count=pr["human_comment_count"],
        category_counts=counts,
        sample_comments=list(samples.values())[:4],
        url=f"https://github.com/{repo}/pull/{number}",
    )