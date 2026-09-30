from src.agent.context import PRContext
from src.agent.graph import facts_block

def test_facts_block_includes_real_numbers():
    ctx = PRContext(
        repo="r", number=1, title="t", author="a",
        idle_days=12.3, waiting_on="reviewer", ttfr_hours=48.0,
        human_comment_count=7, category_counts={"architectural": 3, "nitpick": 2},
        sample_comments=['bob: "why not use X?"'], url="u",
    )
    facts = facts_block(ctx)
    assert "12.3 days" in facts
    assert "architectural: 3" in facts
    assert "waiting on: reviewer" in facts