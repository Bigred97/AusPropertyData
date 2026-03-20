#!/usr/bin/env python3
"""
Verify ingestion can run from your machine.

  Phase 1 — unit tests (parsers, no DB, no network for most)
  Phase 2 — network: scrape data.vic catalogues + probe land.vic/DFFH download (no DB writes)
  Phase 3 — optional DB: if SUPABASE_DB_URL is set and you pass --write-db, run full ingest pipeline

Usage:
  python3 scripts/verify_ingestion_local.py
  python3 scripts/verify_ingestion_local.py --write-db   # needs SUPABASE_DB_URL in env
"""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def run_pytest() -> bool:
    print("\n=== Phase 1: pytest (ingestion parsers) ===\n")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        cwd=ROOT,
    )
    ok = r.returncode == 0
    print("PASS" if ok else "FAIL", "— pytest\n")
    return ok


async def network_smoke() -> bool:
    print("=== Phase 2: catalogue + download probes (no database) ===\n")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from ingestion.dffh_rental import get_rental_download_url
    from ingestion.vpsr_houses import get_latest_download_url
    from ingestion.vpsr_units import get_latest_unit_download_url
    from ingestion.fetch import ingestion_http_client

    ok = True
    h_url: str | None = None
    try:
        h_url, h_label = await get_latest_download_url()
        print(f"  VPSR houses catalogue OK — {h_label[:80]}…")
        print(f"    URL: {h_url[:90]}…")
    except Exception as e:
        print(f"  FAIL VPSR houses catalogue: {e}")
        ok = False

    try:
        u_url, u_label = await get_latest_unit_download_url()
        print(f"  VPSR units catalogue OK — {u_label[:80]}…")
        print(f"    URL: {u_url[:90]}…")
    except Exception as e:
        print(f"  FAIL VPSR units catalogue: {e}")
        ok = False

    try:
        r_url = await get_rental_download_url()
        print("  DFFH rental catalogue OK")
        print(f"    URL: {r_url[:100]}…")
    except Exception as e:
        print(f"  FAIL DFFH catalogue: {e}")
        ok = False

    # Probe binary download (houses) — 403 on some networks is expected
    if h_url:
        try:
            async with ingestion_http_client() as client:
                resp = await client.get(h_url, timeout=60)
            print(
                f"  Land.vic XLS GET status: {resp.status_code} "
                "(200 = scripted download works; 403 = use VPSR_HOUSES_XLS)"
            )
            if resp.status_code == 403:
                print("    Tip: download the .xls in a browser, then:")
                print("    VPSR_HOUSES_XLS=/path/to/file.xls python3 -m ingestion.vpsr_houses")
                print("    In GitHub Actions: add repo secrets VPSR_HOUSES_URL / VPSR_UNITS_URL")
                print("    pointing to HTTPS mirrors (e.g. raw URL from a Release asset).")
        except Exception as e:
            print(f"  WARN land.vic download probe: {e}")

    print()
    return ok


def full_pipeline(*, skip_vpsr_download: bool = False) -> bool:
    print("=== Phase 3: full ingest + recompute (writes to Supabase) ===\n")
    if not os.environ.get("SUPABASE_DB_URL"):
        env_path = ROOT / ".env"
        hint = ""
        if env_path.exists() and env_path.stat().st_size == 0:
            hint = "\n  Hint: `.env` exists but is 0 bytes — save the file in your editor (e.g. Cmd+S)."
        elif not env_path.exists():
            hint = f"\n  Hint: create `{env_path}` (copy from `.env.example`)."
        print(f"  SKIP — SUPABASE_DB_URL not set after loading `.env`.{hint}\n")
        return False
    mods = [
        "ingestion.vpsr_houses",
        "ingestion.vpsr_units",
        "ingestion.dffh_rental",
        "ingestion.recompute_scores",
    ]
    if skip_vpsr_download:
        print(
            "  Skipping VPSR houses/units (land.vic often 403s scripted GET).\n"
            "  Use VPSR_HOUSES_XLS / VPSR_UNITS_XLS or VPSR_*_URL in `.env`, or run without --no-vpsr-download when downloads work.\n"
        )
        mods = [m for m in mods if m not in ("ingestion.vpsr_houses", "ingestion.vpsr_units")]
    for m in mods:
        print(f"  Running: python3 -m {m}")
        r = subprocess.run([sys.executable, "-m", m], cwd=ROOT)
        if r.returncode != 0:
            print(f"  FAIL — {m} exited {r.returncode}\n")
            return False
    print("  PASS — full pipeline finished\n")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--write-db",
        action="store_true",
        help="Run vpsr_houses, vpsr_units, dffh_rental, recompute_scores (requires SUPABASE_DB_URL)",
    )
    ap.add_argument(
        "--no-vpsr-download",
        action="store_true",
        help="With --write-db: skip VPSR modules (use when land.vic returns 403); still runs dffh + recompute",
    )
    args = ap.parse_args()

    os.chdir(ROOT)
    if not run_pytest():
        return 1
    net_ok = asyncio.run(network_smoke())
    if not net_ok:
        print("Fix catalogue/network issues before relying on automated download.\n")
        return 1
    if args.no_vpsr_download and not args.write_db:
        print("error: --no-vpsr-download requires --write-db\n", file=sys.stderr)
        return 2
    if args.write_db:
        if not full_pipeline(skip_vpsr_download=args.no_vpsr_download):
            return 1
    else:
        print(
            "Phase 3 skipped (no DB writes). To test end-to-end on your DB:\n"
            "  python3 scripts/verify_ingestion_local.py --write-db\n"
            "If land.vic blocks scripted VPSR downloads (403), use local .xls paths in `.env` or:\n"
            "  python3 scripts/verify_ingestion_local.py --write-db --no-vpsr-download\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
