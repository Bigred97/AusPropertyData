#!/usr/bin/env python3
"""
Download the latest VPSR house + unit XLS from Data Vic (via CKAN), then optionally
upload them to a GitHub Release so Actions can use VPSR_HOUSES_URL / VPSR_UNITS_URL.

Run from a network where land.vic.gov.au allows scripted GET (usually your laptop).
GitHub Actions runners often get 403 on land.vic — mirroring fixes that.

Usage:
  python3 scripts/publish_vpsr_mirror.py
  python3 scripts/publish_vpsr_mirror.py --out mirror
  python3 scripts/publish_vpsr_mirror.py --gh-release vpsr-mirror   # needs gh CLI + auth
  python3 scripts/publish_vpsr_mirror.py --repo you/AusPropertyData --gh-release vpsr-mirror

If land.vic returns 403 (scripted GET blocked), download both XLS via the catalogue in a
browser, then point at the saved files:

  python3 scripts/publish_vpsr_mirror.py --houses-xls ~/Downloads/median-house-q2-2025.xls \\
      --units-xls ~/Downloads/median-unit-q2-2025.xls --gh-release vpsr-mirror

After upload, set repo secrets (replace OWNER/REPO and filenames):
  VPSR_HOUSES_URL=https://github.com/OWNER/REPO/releases/download/vpsr-mirror/<file>.xls
  VPSR_UNITS_URL=https://github.com/OWNER/REPO/releases/download/vpsr-mirror/<file>.xls

See docs/AUTOMATION.md § VPSR mirror for CI.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.vpsr_ckan import (  # noqa: E402
    HOUSES_CATALOGUE_URL,
    UNITS_CATALOGUE_URL,
    ckan_client,
    download_land_vic_xls,
    latest_houses_resource,
    latest_units_resource,
)


def _safe_filename_from_url(url: str, fallback: str) -> str:
    path = urlparse(url).path
    base = Path(path).name
    if base and re.match(r"^[\w.\-]+\.xls$", base, re.I):
        return base
    return fallback


def _git_slug() -> str | None:
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        url = r.stdout.strip()
        m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    except OSError:
        pass
    return None


def _gh_repo_slug() -> str | None:
    """When cwd is a gh-linked repo, resolve owner/name (works if git remote is missing)."""
    gh = shutil.which("gh")
    if not gh:
        return None
    try:
        r = subprocess.run(
            [gh, "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except OSError:
        pass
    return None


def _resolve_slug(repo_arg: str | None) -> str | None:
    if repo_arg:
        s = repo_arg.strip().strip("/")
        return s if "/" in s else None
    return _git_slug() or _gh_repo_slug()


def _is_placeholder_repo(slug: str) -> bool:
    u = slug.upper()
    return (
        "YOUR_GITHUB_USER" in u
        or "YOUR_REPO" in u
        or "OWNER/REPO" in u
        or u.startswith("YOUR_")
    )


def _in_git_repo() -> bool:
    return (ROOT / ".git").is_dir()


def _gh_prefix(slug: str | None) -> list[str]:
    """gh needs -R when cwd is not a git repo (or to disambiguate)."""
    gh = shutil.which("gh")
    if not gh:
        return []
    cmd = [gh]
    if slug:
        cmd.extend(["-R", slug])
    return cmd


def main() -> int:
    p = argparse.ArgumentParser(description="Publish VPSR XLS mirrors for CI")
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "mirror",
        help="Directory to write .xls files (default: ./mirror)",
    )
    p.add_argument(
        "--houses-xls",
        type=Path,
        metavar="PATH",
        help="Use this file instead of HTTP download (e.g. saved from browser)",
    )
    p.add_argument(
        "--units-xls",
        type=Path,
        metavar="PATH",
        help="Use this file instead of HTTP download",
    )
    p.add_argument(
        "--gh-release",
        metavar="TAG",
        help="Create or update this GitHub release and upload both files (requires gh CLI)",
    )
    p.add_argument(
        "--repo",
        metavar="OWNER/NAME",
        help="GitHub repo for secret URL hints (use if this folder has no git remote), e.g. you/AusPropertyData",
    )
    args = p.parse_args()
    out_dir: Path = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    local_h = args.houses_xls
    local_u = args.units_xls
    if (local_h is None) ^ (local_u is None):
        print(
            "Error: pass both --houses-xls and --units-xls, or neither for CKAN download.",
            file=sys.stderr,
        )
        return 2

    if local_h and local_u:
        h_expanded = local_h.expanduser()
        u_expanded = local_u.expanduser()
        if not h_expanded.is_file() or not u_expanded.is_file():
            print(
                "Error: --houses-xls and --units-xls must be real paths to files on disk.",
                file=sys.stderr,
            )
            if "path/to" in str(local_h) or "path/to" in str(local_u) or "...." in str(local_h):
                print(
                    "  (You copied the doc placeholder — use your actual save location, e.g.\n"
                    "   ~/Downloads/median-house-q2-2025.xls)",
                    file=sys.stderr,
                )
            else:
                print(f"  houses: {h_expanded} → exists={h_expanded.is_file()}", file=sys.stderr)
                print(f"  units:  {u_expanded} → exists={u_expanded.is_file()}", file=sys.stderr)
            return 2
        local_h, local_u = h_expanded, u_expanded
        h_path = out_dir / local_h.name
        u_path = out_dir / local_u.name
        h_path.write_bytes(local_h.read_bytes())
        u_path.write_bytes(local_u.read_bytes())
        print(f"Houses: copied {local_h} → {h_path}")
        print(f"Units:  copied {local_u} → {u_path}\n")
    else:
        with ckan_client() as client:
            hr = latest_houses_resource(client)
            ur = latest_units_resource(client)
            h_url = hr["url"]
            u_url = ur["url"]
            h_name = _safe_filename_from_url(h_url, "vpsr-houses-latest.xls")
            u_name = _safe_filename_from_url(u_url, "vpsr-units-latest.xls")

            print(f"Houses: {hr.get('name')} → {h_url}")
            print(f"Units:  {ur.get('name')} → {u_url}\n")

            h_path = out_dir / h_name
            u_path = out_dir / u_name

            try:
                print("Downloading houses…")
                h_path.write_bytes(
                    download_land_vic_xls(
                        client, h_url, referer_catalogue_url=HOUSES_CATALOGUE_URL
                    )
                )
                print(f"  Wrote {h_path} ({h_path.stat().st_size} bytes)")

                print("Downloading units…")
                u_path.write_bytes(
                    download_land_vic_xls(
                        client, u_url, referer_catalogue_url=UNITS_CATALOGUE_URL
                    )
                )
                print(f"  Wrote {u_path} ({u_path.stat().st_size} bytes)")
            except Exception as e:
                print(
                    f"\nDownload failed ({e}).\n"
                    "land.vic often blocks scripted requests. Save both .xls from the Data Vic "
                    "catalogue in your browser, then re-run with your real paths, e.g.\n"
                    f"  python3 scripts/publish_vpsr_mirror.py \\\n"
                    f"    --houses-xls ~/Downloads/{h_name} \\\n"
                    f"    --units-xls ~/Downloads/{u_name}\n",
                    file=sys.stderr,
                )
                return 1

    slug = _resolve_slug(args.repo)
    tag_for_urls = args.gh_release or "<TAG>"
    houses_asset = h_path.name
    units_asset = u_path.name

    print("\n--- Set GitHub Actions secrets (or .env for local) ---")
    if slug:
        prefix = f"https://github.com/{slug}/releases/download/{tag_for_urls}"
        print(f"VPSR_HOUSES_URL={prefix}/{houses_asset}")
        print(f"VPSR_UNITS_URL={prefix}/{units_asset}")
    else:
        print(
            f"VPSR_HOUSES_URL=https://github.com/OWNER/REPO/releases/download/{tag_for_urls}/"
            + houses_asset
        )
        print(
            f"VPSR_UNITS_URL=https://github.com/OWNER/REPO/releases/download/{tag_for_urls}/"
            + units_asset
        )
        print(
            "\n(Replace OWNER/REPO with your GitHub repo, or re-run with "
            "--repo your-user/your-repo for exact URLs.)",
        )

    if args.gh_release:
        tag = args.gh_release
        if not shutil.which("gh"):
            print(
                "\n--- gh CLI not found — mirror files are ready ---\n"
                f"  {h_path}\n"
                f"  {u_path}\n\n"
                "Install GitHub CLI (macOS):\n"
                "  brew install gh\n"
                "  gh auth login\n\n"
                "Then re-run the same command (with --gh-release) to upload.\n\n"
                "Or in the browser: GitHub repo → Releases → New release → "
                f"tag {tag!r} → attach the two files above → publish.\n",
                file=sys.stderr,
            )
            return 1

        gh_slug = slug
        if gh_slug and _is_placeholder_repo(gh_slug):
            print(
                f"Error: --repo looks like a doc placeholder ({gh_slug!r}). "
                "Use your real GitHub repo, e.g. --repo Bigred97/AusPropertyData",
                file=sys.stderr,
            )
            return 2
        if not gh_slug and not _in_git_repo():
            print(
                "Error: this folder is not a git repository, so gh cannot tell which "
                "repo to use. Pass your real repo, e.g.\n"
                "  --repo YOUR_USERNAME/AusPropertyData",
                file=sys.stderr,
            )
            return 2
        # Without -R, gh release fails with "fatal: not a git repository" when .git is missing.
        if not gh_slug and _in_git_repo():
            gh_slug = _git_slug() or _gh_repo_slug()
        if not gh_slug:
            print(
                "Error: could not resolve owner/repo for gh. Pass --repo owner/name.",
                file=sys.stderr,
            )
            return 2

        prefix = _gh_prefix(gh_slug)
        # Ensure release exists (idempotent)
        view = subprocess.run(
            [*prefix, "release", "view", tag],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if view.returncode != 0:
            notes = "Mirrored VPSR XLS for CI — see docs/AUTOMATION.md"
            cr = subprocess.run(
                [*prefix, "release", "create", tag, "--title", tag, "--notes", notes],
                cwd=ROOT,
            )
            if cr.returncode != 0:
                return cr.returncode
        up = subprocess.run(
            [
                *prefix,
                "release",
                "upload",
                tag,
                str(h_path),
                str(u_path),
                "--clobber",
            ],
            cwd=ROOT,
        )
        if up.returncode != 0:
            return up.returncode
        print(f"\nUploaded to release {tag!r} on {gh_slug}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
