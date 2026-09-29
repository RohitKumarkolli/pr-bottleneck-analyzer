import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from src.config import GITHUB_TOKEN, TARGET_REPO

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

def main():
    # 1. Rate limit / token sanity check
    r = requests.get("https://api.github.com/rate_limit", headers=HEADERS)
    r.raise_for_status()
    core = r.json()["resources"]["core"]
    print(f"Token OK. Rate limit: {core['remaining']}/{core['limit']} remaining")

    # 2. Count open PRs via the search API (one cheap call)
    q = f"repo:{TARGET_REPO} is:pr is:open"
    r = requests.get("https://api.github.com/search/issues",
                     headers=HEADERS, params={"q": q, "per_page": 1})
    r.raise_for_status()
    print(f"{TARGET_REPO}: {r.json()['total_count']} open PRs")

    # 3. Count PRs merged in the last 60 days
    q = f"repo:{TARGET_REPO} is:pr is:merged merged:>=2026-08-01"
    r = requests.get("https://api.github.com/search/issues",
                     headers=HEADERS, params={"q": q, "per_page": 1})
    r.raise_for_status()
    print(f"{TARGET_REPO}: {r.json()['total_count']} PRs merged since 2026-08-01")

if __name__ == "__main__":
    main()