import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.config import TARGET_REPO
from dashboard.data import load_metrics, load_labels

st.set_page_config(page_title="PR Bottleneck Analyzer", layout="wide")

metrics = load_metrics()
labels = load_labels()

if metrics.empty:
    st.error("No data in pr_metrics. Run `python -m src.metrics.compute` first.")
    st.stop()

st.title("PR Bottleneck Analyzer")
st.caption(f"Repo: {TARGET_REPO}")

# ---------------- Sidebar filters ----------------
st.sidebar.header("Filters")
state_choice = st.sidebar.radio("PR state", ["Open only", "All"], index=0)
min_idle = st.sidebar.slider("Min idle days (open PRs)", 0, 30, 0)

open_prs = metrics[(metrics["state"] == "open") & (metrics["draft"] == 0)].copy()
open_prs["idle_days"] = (open_prs["idle_hours"] / 24).round(1)
open_prs = open_prs[open_prs["idle_days"] >= min_idle]

df = metrics if state_choice == "All" else metrics[metrics["state"] == "open"]

# ---------------- Top-line numbers ----------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total PRs", len(metrics))
c1.caption(f"{len(metrics[metrics['state']=='open'])} open")
c2.metric("Stalled PRs", int(metrics["is_stalled"].sum()))
c2.caption(f"of {len(open_prs) if min_idle==0 else int((metrics['state']=='open').sum())} open non-draft")
med_ttfr = metrics["ttfr_hours"].median()
c3.metric("Median TTFR", f"{med_ttfr/24:.1f}d" if med_ttfr == med_ttfr else "n/a")
med_ttm = metrics["ttm_hours"].median()
c4.metric("Median TTM", f"{med_ttm/24:.1f}d" if med_ttm == med_ttm else "n/a")

st.divider()

tab1, tab2, tab3 = st.tabs(["🚧 Blocked PRs", "🏆 Idle-Time Leaderboard", "💬 Comment Categories"])

# ---------------- Tab 1: Blocked PRs ----------------
with tab1:
    st.subheader("Stalled PRs, most idle first")
    blocked = open_prs[open_prs["is_stalled"] == 1].sort_values("idle_days", ascending=False)
    if blocked.empty:
        st.success("No stalled PRs match the current filters.")
    else:
        show = blocked[["number", "author", "waiting_on", "idle_days", "human_comment_count", "url"]].rename(
            columns={"number": "PR", "author": "Author", "waiting_on": "Waiting on",
                     "idle_days": "Idle (days)", "human_comment_count": "Comments", "url": "Link"})
        st.dataframe(show, width='stretch', hide_index=True,
                     column_config={"Link": st.column_config.LinkColumn(display_text="Open ↗")})

# ---------------- Tab 2: Leaderboards ----------------
with tab2:
    waiting_reviewer = blocked = open_prs[open_prs["waiting_on"] == "reviewer"] if not open_prs.empty else open_prs
    waiting_author = open_prs[open_prs["waiting_on"] == "author"] if not open_prs.empty else open_prs

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Authors with the most idle time** (PR waiting on them)")
        if waiting_author.empty:
            st.info("No PRs currently waiting on their author.")
        else:
            lb = waiting_author.groupby("author")["idle_days"].agg(["sum", "count"]).reset_index()
            lb.columns = ["Author", "Total idle days", "PR count"]
            st.dataframe(lb.sort_values("Total idle days", ascending=False).head(10),
                        width='stretch', hide_index=True)
    with col2:
        st.markdown("**PRs waiting longest on a reviewer** (no assigned-reviewer data yet, so shown by PR)")
        if waiting_reviewer.empty:
            st.info("No PRs currently waiting on a reviewer.")
        else:
            lb2 = waiting_reviewer[["number", "author", "idle_days"]].sort_values(
                "idle_days", ascending=False).head(10)
            lb2.columns = ["PR", "Author", "Idle days"]
            st.dataframe(lb2, width='stretch', hide_index=True)
    st.caption("Note: GitHub's requested-reviewers data isn't ingested yet (see README limitations), "
              "so the reviewer side is shown per-PR rather than per-person.")

# ---------------- Tab 3: Comment categories ----------------
with tab3:
    if labels.empty:
        st.warning("No classified comments yet. Run `python -m src.classifier.classify`.")
    else:
        import plotly.express as px
        counts = labels["category"].value_counts().reset_index()
        counts.columns = ["Category", "Count"]
        fig = px.bar(counts, x="Category", y="Count", color="Category",
                     category_orders={"Category": ["nitpick", "architectural", "question", "approval", "other"]})
        st.plotly_chart(fig, width='stretch')

        st.markdown("**Filter by PR**")
        pr_options = sorted(labels["pr_number"].unique())
        pick = st.selectbox("PR number", ["All"] + list(pr_options))
        shown = labels if pick == "All" else labels[labels["pr_number"] == pick]
        st.dataframe(
            shown[["pr_number", "category", "author", "kind", "body"]].rename(
                columns={"pr_number": "PR", "category": "Category", "author": "Author",
                        "kind": "Type", "body": "Comment"}),
            width='stretch', hide_index=True, height=400)