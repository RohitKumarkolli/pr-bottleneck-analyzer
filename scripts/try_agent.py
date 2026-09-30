# scripts/try_agent.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import TARGET_REPO
from src.agent.graph import run_for_pr

result = run_for_pr(TARGET_REPO, int(sys.argv[1]))
print("DIAGNOSIS:", result["diagnosis"].model_dump_json(indent=2))
print("\nNUDGE:", result["nudge"].message)