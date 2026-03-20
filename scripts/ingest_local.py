#!/usr/bin/env python3
"""
Best-effort ingestion from your machine (loads repo `.env`).

  python3 scripts/ingest_local.py

Runs in order: DFFH rental (download works from dffh.vic.gov.au) → recompute_scores →
VPSR houses → VPSR units. If land.vic returns 403, set `VPSR_HOUSES_XLS` /
`VPSR_UNITS_XLS` in `.env` to files you saved from a browser, or `VPSR_*_URL`
mirrors — then re-run.

This is a thin wrapper so you do not need to remember four module names.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    "ingestion.dffh_rental",
    "ingestion.recompute_scores",
    "ingestion.vpsr_houses",
    "ingestion.vpsr_units",
]


def main() -> int:
    load_dotenv(ROOT / ".env")
    for mod in STEPS:
        print(f"\n>>> python3 -m {mod}\n")
        r = subprocess.run([sys.executable, "-m", mod], cwd=ROOT)
        if r.returncode != 0:
            print(f"\nStopped: {mod} exited {r.returncode}", file=sys.stderr)
            return r.returncode
    print("\n>>> All ingestion steps finished OK.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
