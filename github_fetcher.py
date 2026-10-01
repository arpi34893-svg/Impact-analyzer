import os
import sys
import json
import time
import traceback
import requests

GITHUB_API = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

TIMEOUT = 10
OUTPUT_FILE = "training_data.json"


def discover_active_python_repos(min_stars: int = 500, max_stars: int = 5000, limit: int = 30) -> list:
    query = f"language:Python stars:{min_stars}..{max_stars} pushed:>2026-01-01"
    url = f"{GITHUB_API}/search/repositories"
    params = {"q": query, "sort": "updated", "order": "desc", "per_page": min(limit, 100)}

    response = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
    print(f"[debug] search status: {response.status_code}", flush=True)
    response.raise_for_status()
    data = response.json()

    return [item["full_name"] for item in data.get("items", [])][:limit]


def fetch_merged_prs(repo_full_name: str, max_prs: int = 20) -> list:
    prs_url = f"{GITHUB_API}/repos/{repo_full_name}/pulls"
    params = {"state": "closed", "sort": "updated", "direction": "desc", "per_page": max_prs}

    response = requests.get(prs_url, headers=HEADERS, params=params, timeout=TIMEOUT)
    print(f"[debug] pulls status for {repo_full_name}: {response.status_code}", flush=True)
    if response.status_code != 200:
        return []
    pr_list = response.json()

    results = []
    for pr in pr_list:
        if not pr.get("merged_at"):
            continue

        pr_number = pr["number"]
        files_url = f"{GITHUB_API}/repos/{repo_full_name}/pulls/{pr_number}/files"
        files_response = requests.get(files_url, headers=HEADERS, timeout=TIMEOUT)
        if files_response.status_code != 200:
            continue

        changed_files = [f["filename"] for f in files_response.json() if f["filename"].endswith(".py")]
        if len(changed_files) >= 2:
            results.append({"pr_number": pr_number, "files": changed_files})

        time.sleep(0.3)

    return results


def build_training_dataset(repos: list, max_prs_per_repo: int = 20) -> dict:
    """
    Loops over every discovered repo, fetches its merged PRs, and combines
    everything into one dataset keyed by repo name.
    """
    dataset = {}
    for i, repo in enumerate(repos, start=1):
        print(f"\n[{i}/{len(repos)}] Fetching merged PRs for {repo}...", flush=True)
        try:
            prs = fetch_merged_prs(repo, max_prs=max_prs_per_repo)
            print(f"  -> Found {len(prs)} PRs with 2+ Python files changed", flush=True)
            if prs:
                dataset[repo] = prs
        except Exception as e:
            print(f"  -> Skipping {repo} due to error: {e}", flush=True)
            continue
    return dataset


if __name__ == "__main__":
    if not TOKEN:
        print("[warning] No GITHUB_TOKEN set — unauthenticated requests are rate-limited to ~10/min for search.", flush=True)

    try:
        print("Discovering active Python repos...", flush=True)
        repos = discover_active_python_repos(limit=30)  # full batch now
        print(f"Found {len(repos)} repos:", flush=True)
        for r in repos:
            print(f"  - {r}", flush=True)

        if not repos:
            print("No repos found — check your search query filters.", flush=True)
            sys.exit(0)

        dataset = build_training_dataset(repos, max_prs_per_repo=20)

        total_prs = sum(len(v) for v in dataset.values())
        print(f"\nDone. Collected {total_prs} qualifying PRs across {len(dataset)} repos.", flush=True)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)
        print(f"Saved combined dataset to {OUTPUT_FILE}", flush=True)

    except Exception:
        print("\n[ERROR] Script failed with an exception:\n", flush=True)
        traceback.print_exc()
        sys.exit(1)