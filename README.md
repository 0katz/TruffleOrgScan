# TruffleOrgScan 

**TruffleOrgScan** is a wrapper script that automates secret scanning across multiple organizations in a GitHub Enterprise environment using [TruffleHog](https://github.com/trufflesecurity/trufflehog). It fetches organizations, enumerates their repositories, and runs TruffleHog scans, helping you quickly identify potential secrets across a large number of internal repositories.

## Features

- Fetches all organizations accessible to your Personal Access Token (PAT) from GitHub Enterprise.
- Uses GraphQL to list repositories within each organization.
- Automates running TruffleHog against all discovered repositories.
- Organizes scan results in a structured directory, logging failures and skipped organizations.

## Requirements

- **Git**: Required by TruffleHog for repository operations.
- **TruffleHog**: Install via `pip install trufflehog` or place a `trufflehog` (or `trufflehog.exe` on Windows) binary in the working directory.
- **Python 3** with `requests`:
  ```bash
  pip install requests
  ```
- A GitHub Enterprise Personal Access Token (PAT) with the following scopes:
  - `repo: Full Control`
  - `read:org`

## Setup

1. Open `run_all.py` and:
   - Set `TOKEN` to your GitHub Enterprise PAT.
   - Update `BASE_GITHUB_URL` to match your GitHub Enterprise instance (e.g., `https://git.example.com`).
   - Ensure `trufflehog` is available and `git` is installed.

2. Run:
   ```bash
   python run_all.py
   ```

## What Happens

1. If `unique_orgs.txt` exists and is non-empty, the script uses it as the organization list. Otherwise, it fetches all accessible organizations.
2. For each organization, it uses GraphQL to enumerate repositories and then runs TruffleHog against them.
3. Results are stored under `trufflehog_results/` with separate directories per organization.

## Output Structure

- `trufflehog_results/`: One directory per organization, each containing `*_trufflehog_results.log`.
- `failed_orgs.txt`: Organizations where the TruffleHog scan failed.
- `skipped_empty_orgs.txt`: Organizations with no repositories.

## Troubleshooting

- **INSUFFICIENT_SCOPES**: Update your PAT to include missing scopes.
- **Binary File Timeouts**: If TruffleHog times out on large binary files, consider excluding them or adjusting TruffleHog’s configuration.
- **Rate Limits**: If you hit rate limits, implement caching/delays.
