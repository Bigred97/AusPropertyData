#!/usr/bin/env python3
"""
Push SUPABASE_DB_URL from repo .env to GitHub Actions secrets (never prints the URL).

  python3 scripts/sync_supabase_secret_to_github.py
  python3 scripts/sync_supabase_secret_to_github.py --repo Bigred97/AusPropertyData

Requires: gh CLI authenticated (`gh auth login`).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description="Sync SUPABASE_DB_URL to gh secret")
    p.add_argument(
        "--repo",
        default="Bigred97/AusPropertyData",
        help="owner/name (default: Bigred97/AusPropertyData)",
    )
    args = p.parse_args()

    env_path = ROOT / ".env"
    if not env_path.is_file():
        print("ERROR: .env not found at", env_path, file=sys.stderr)
        return 1

    val = None
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("SUPABASE_DB_URL="):
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

    if not val:
        print("ERROR: SUPABASE_DB_URL missing in .env", file=sys.stderr)
        return 1

    subprocess.run(
        ["gh", "secret", "set", "SUPABASE_DB_URL", "-R", args.repo, "--body", val],
        cwd=ROOT,
        check=True,
    )
    print(f"OK: SUPABASE_DB_URL set on GitHub repo {args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
