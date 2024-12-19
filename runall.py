import os
import subprocess
import requests
import sys
import platform

TOKEN = "<token>"
BASE_GITHUB_URL = "https://<url>"  # Replace with your GHE URL (e.g., https://git.example.com)
RESULTS_DIR = "./trufflehog_results"

HEADERS = {
    "Authorization": f"token {TOKEN}"
}

REST_ENDPOINT = f"{BASE_GITHUB_URL}/api/v3"
GRAPHQL_ENDPOINT = f"{BASE_GITHUB_URL}/api/graphql"

# On Windows, if you have trufflehog.exe in the current directory:
if platform.system().lower().startswith("win"):
    TRUFFLEHOG_CMD = "./trufflehog.exe"
else:
    # On Linux/macOS, usually just 'trufflehog' if it's in PATH
    TRUFFLEHOG_CMD = "trufflehog"

def fetch_all_organizations():
    """
    Fetch all organizations from the given GitHub instance using the REST API.
    If unique_orgs.txt exists and is not empty, skip re-fetching.
    """
    if os.path.exists("unique_orgs.txt") and os.path.getsize("unique_orgs.txt") > 0:
        print("unique_orgs.txt already exists and is not empty. Skipping fetching.")
        with open("unique_orgs.txt", "r") as f:
            unique_orgs = [line.strip() for line in f if line.strip()]
        return unique_orgs

    all_orgs = []
    next_url = f"{REST_ENDPOINT}/organizations?per_page=100"
    
    while next_url:
        print(f"[DEBUG] Fetching organizations: {next_url}")
        resp = requests.get(next_url, headers=HEADERS)
        if resp.status_code != 200:
            print(f"[ERROR] Failed to fetch organizations: {resp.status_code} {resp.text}")
            break

        orgs_page = resp.json()
        for org in orgs_page:
            if 'login' in org:
                all_orgs.append(org['login'])

        link_header = resp.headers.get('Link', '')
        next_link = None
        if link_header:
            parts = link_header.split(',')
            for p in parts:
                if 'rel="next"' in p:
                    next_link = p[p.index('<')+1:p.index('>')]
                    break
        next_url = next_link if next_link else None

    unique_orgs = sorted(set(all_orgs))
    with open("unique_orgs.txt", "w") as f:
        for o in unique_orgs:
            f.write(o + "\n")
    print("[DEBUG] All unique organizations saved to unique_orgs.txt")
    return unique_orgs

def fetch_org_repos_graphql(org):
    print(f"[DEBUG] Fetching repos for org: {org}")
    query = """
    query($org: String!, $after: String) {
      organization(login: $org) {
        repositories(first: 100, after: $after) {
          pageInfo {
            endCursor
            hasNextPage
          }
          nodes {
            name
          }
        }
      }
    }
    """

    repos = []
    after = None
    while True:
        variables = {
            "org": org,
            "after": after
        }
        try:
            resp = requests.post(
                GRAPHQL_ENDPOINT,
                headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
                json={"query": query, "variables": variables},
                timeout=30
            )
        except requests.RequestException as e:
            print(f"[ERROR] GraphQL query failed for {org}: {e}")
            return []

        if resp.status_code != 200:
            print(f"[ERROR] GraphQL query failed for {org}: {resp.status_code} {resp.text}")
            return []

        data = resp.json()
        if "errors" in data:
            print(f"[DEBUG] GraphQL errors for {org}: {data['errors']}")
            return []

        org_data = data.get("data", {}).get("organization")
        if not org_data:
            # Organization not accessible or no access
            print(f"[DEBUG] No org_data returned for {org}, possibly no access or org doesn't exist.")
            return []

        repo_data = org_data["repositories"]
        for r in repo_data["nodes"]:
            repos.append(r["name"])

        if repo_data["pageInfo"]["hasNextPage"]:
            after = repo_data["pageInfo"]["endCursor"]
            print(f"[DEBUG] {org} has more repos, fetching next page...")
        else:
            break

    print(f"[DEBUG] Found {len(repos)} repos for org: {org}")
    return repos

def run_trufflehog(org):
    """
    Run TruffleHog against the given organization using the local trufflehog binary.
    """
    print(f"[DEBUG] Preparing to run TruffleHog for {org}")
    org_dir = os.path.join(RESULTS_DIR, org)
    if os.path.isdir(org_dir):
        print(f"Skipping {org}: Folder already exists.")
        return

    repos = fetch_org_repos_graphql(org)
    if not repos:
        print(f"Skipping {org}: No repositories found.")
        with open("skipped_empty_orgs.txt", "a") as f:
            f.write(f"{org}\n")
        return

    os.makedirs(org_dir, exist_ok=True)
    output_file = os.path.join(org_dir, f"{org}_trufflehog_results.log")
    print(f"[DEBUG] Running TruffleHog for organization: {org}")
    
    cmd = [
        TRUFFLEHOG_CMD,
        "github",
        "--token", TOKEN,
        "--org", org,
        "--no-update",
        "--endpoint", BASE_GITHUB_URL
    ]

    print(f"[DEBUG] Command to run: {' '.join(cmd)}")

    try:
        with open(output_file, "w") as out:
            subprocess.check_call(cmd, stdout=out, stderr=subprocess.STDOUT)
        print(f"Results saved to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"TruffleHog failed for {org}. See {output_file} for details.")
        with open("failed_orgs.txt", "a") as f:
            f.write(f"{org}\n")
        print(f"[ERROR] Subprocess error: {e}")

def main():
    unique_orgs = fetch_all_organizations()

    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    print("[DEBUG] Starting scans for all organizations...")
    for org in unique_orgs:
        print(f"[DEBUG] Processing organization: {org}")
        run_trufflehog(org)
        sys.stdout.flush()

if __name__ == "__main__":
    main()