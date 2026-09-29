import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import pandas as pd
import streamlit as st

from src.config import DB_PATH, TARGET_REPO

@st.cache_data(ttl=300)  # 5 min: long enough to avoid re-querying every rerun, short enough to pick up a fresh daily-cron run
def load_metrics(repo=TARGET_REPO) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM pr_metrics WHERE repo = ?", conn, params=(repo,))
    conn.close()
    for col in ["created_at", "first_response_at", "merged_at", "last_activity_at"]:
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    df["url"] = f"https://github.com/{repo}/pull/" + df["number"].astype(str)
    return df


@st.cache_data(ttl=300)
def load_labels(repo=TARGET_REPO) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """SELECT l.category, l.reason, c.pr_number, c.author, c.kind, c.body
           FROM comment_labels l
           JOIN comments c ON c.repo=l.repo AND c.kind=l.kind AND c.id=l.id
           WHERE l.repo = ?""",
        conn, params=(repo,))
    conn.close()
    return df