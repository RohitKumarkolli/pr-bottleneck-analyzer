import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "prs.db"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
TARGET_REPO = os.getenv("TARGET_REPO", "scikit-learn/scikit-learn")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# How far back to pull closed/merged PRs (used from Milestone 1 onward)
LOOKBACK_DAYS = 60
# Cap per state (open / closed) so the first runs stay small and cheap
MAX_PRS_PER_STATE = int(os.getenv("MAX_PRS_PER_STATE", "300"))
# A PR with no human activity for this long (and not a draft) counts as stalled
STALL_DAYS = int(os.getenv("STALL_DAYS", "7"))

if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN missing. Copy .env.example to .env and fill it in.")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
# Seconds between LLM calls, to stay under Groq's requests-per-minute limit
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "2.0"))