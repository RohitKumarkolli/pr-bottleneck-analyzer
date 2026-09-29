import time
import requests
from src.config import GITHUB_TOKEN

BASE = "https://api.github.com"

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})

api_calls = 0  # tracked for the README ("ingested N PRs in M API calls")


def _request(url, params=None):
    global api_calls
    for attempt in range(5):
        r = session.get(url, params=params, timeout=30)
        api_calls += 1

        if r.status_code in (403, 429):
            # Primary rate limit exhausted: sleep until reset
            if r.headers.get("X-RateLimit-Remaining") == "0":
                wait = int(r.headers["X-RateLimit-Reset"]) - time.time() + 5
                print(f"  Rate limit hit. Sleeping {int(wait)}s...")
                time.sleep(max(wait, 1))
                continue
            # Secondary rate limit: honor Retry-After
            if r.headers.get("Retry-After"):
                time.sleep(int(r.headers["Retry-After"]) + 1)
                continue
        if r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue

        r.raise_for_status()
        return r
    raise RuntimeError(f"Failed after retries: {url}")


def paginate(path, params=None):
    """Lazy generator over all pages, so callers can `break` and stop fetching."""
    url = BASE + path
    params = {"per_page": 100, **(params or {})}
    while url:
        r = _request(url, params)
        yield from r.json()
        url = r.links.get("next", {}).get("url")
        params = None  # the next-URL already carries the query string