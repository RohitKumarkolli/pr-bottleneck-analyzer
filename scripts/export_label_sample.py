import csv
import json
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import ROOT, TARGET_REPO
from src.classifier.classify import fetch_eligible
from src.ingestion.db import get_conn

N, DEV_N, SEED = 60, 20, 42
OUT = ROOT / "data" / "labeled_comments.csv"


def main():
    if OUT.exists():
        sys.exit(f"{OUT} already exists. Delete it on purpose if you want a new sample "
                 "(you'd lose your labels).")
    rows = fetch_eligible(get_conn(), TARGET_REPO)
    random.Random(SEED).shuffle(rows)      # fixed seed = reproducible sample
    sample = rows[:N]

    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["kind", "id", "pr_number", "split", "pr_title", "url", "body", "label"])
        for i, r in enumerate(sample):
            url = json.loads(r["raw_json"]).get("html_url", "")
            w.writerow([r["kind"], r["id"], r["pr_number"],
                        "dev" if i < DEV_N else "test",
                        r["pr_title"], url, r["body"], ""])
    print(f"Wrote {len(sample)} comments to {OUT} "
          f"({DEV_N} dev, {len(sample) - DEV_N} test) from {len(rows)} eligible")


if __name__ == "__main__":
    main()