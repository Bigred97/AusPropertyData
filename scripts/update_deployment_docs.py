#!/usr/bin/env python3
"""
Refresh docs/DEPLOYMENT.md from Railway + Supabase CLIs (non-secret fields only).
Requires: railway CLI linked to this project; supabase CLI logged in.

Usage (from repo root):
  python3 scripts/update_deployment_docs.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "DEPLOYMENT.md"


def run(cmd: list[str], cwd: Path) -> str:
    p = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr or p.stdout}")
    return p.stdout


def redact_db_url(url: str) -> str:
    """Mask password in postgres URL if present."""
    if not url or url == "null":
        return "(not set)"
    return re.sub(r":([^:@/]+)@", r":***@", url, count=1)


def parse_supabase_projects_table(text: str) -> dict[str, str] | None:
    """Parse `supabase projects list` table for first data row."""
    for ln in text.splitlines():
        if "REFERENCE ID" in ln or not ln.strip() or set(ln.strip()) <= {"|", "-", " "}:
            continue
        cells = [c.strip() for c in ln.split("|")]
        # Leading/trailing empty from table borders
        while cells and cells[0] == "":
            cells.pop(0)
        while cells and cells[-1] == "":
            cells.pop()
        # LINKED | ORG | REF (20 chars) | NAME | REGION | CREATED
        # Leading empty cell from "| org |" is popped; then [0]=org, [1]=ref, ...
        if len(cells) >= 4 and re.match(r"^[a-z]{20}$", cells[1]):
            return {
                "org_id": cells[0],
                "ref": cells[1],
                "name": cells[2],
                "region": cells[3],
            }
    return None


def main() -> int:
    cwd = ROOT
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    try:
        status = run(["railway", "status"], cwd).strip()
    except FileNotFoundError:
        print("Install Railway CLI: https://docs.railway.com/guides/cli", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1

    try:
        raw_json = run(["railway", "variable", "list", "--json"], cwd)
        rvars = json.loads(raw_json)
    except (RuntimeError, json.JSONDecodeError) as e:
        print(f"Railway variables: {e}", file=sys.stderr)
        rvars = {}

    supabase_block = ""
    try:
        sb_out = run(["supabase", "projects", "list"], cwd)
        proj = parse_supabase_projects_table(sb_out)
        if proj:
            ref = proj["ref"]
            supabase_block = f"""
### Supabase (from `supabase projects list`)

| Field | Value |
|-------|-------|
| Project name | `{proj["name"]}` |
| Project ref | `{ref}` |
| Region | {proj["region"]} |
| Dashboard | [Open project](https://supabase.com/dashboard/project/{ref}) |
| DB pooler (typical host) | `aws-1-ap-southeast-2.pooler.supabase.com` |

Connection string shape (password **never** committed):

`postgresql://postgres.{ref}:***@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres`
"""
    except FileNotFoundError:
        supabase_block = "\n### Supabase\n\n_Supabase CLI not installed or not on PATH._\n"
    except RuntimeError as e:
        supabase_block = f"\n### Supabase\n\n_Could not list projects: {e}_\n"

    public_domain = rvars.get("RAILWAY_PUBLIC_DOMAIN", "")
    api_base = f"https://{public_domain}" if public_domain else "(run from linked Railway project)"

    db_redacted = redact_db_url(rvars.get("SUPABASE_DB_URL", ""))

    md = f"""# Deployment reference

_Generated: {generated_at} — run `python3 scripts/update_deployment_docs.py` to refresh._

## Railway (`railway status`)

```
{status}
```

### Railway variables (sanitized)

| Variable | Value |
|----------|-------|
| `RAILWAY_PROJECT_NAME` | `{rvars.get("RAILWAY_PROJECT_NAME", "")}` |
| `RAILWAY_PROJECT_ID` | `{rvars.get("RAILWAY_PROJECT_ID", "")}` |
| `RAILWAY_SERVICE_NAME` | `{rvars.get("RAILWAY_SERVICE_NAME", "")}` |
| `RAILWAY_SERVICE_ID` | `{rvars.get("RAILWAY_SERVICE_ID", "")}` |
| `RAILWAY_PUBLIC_DOMAIN` | `{public_domain}` |
| `ENV` | `{rvars.get("ENV", "")}` |
| `CORS_ORIGINS` | `{rvars.get("CORS_ORIGINS", "")}` |
| `SUPABASE_DB_URL` | `{db_redacted}` |

### API

- **Base URL:** `{api_base}`
- **Health:** `{api_base}/health`

{supabase_block}

## Security

- Do **not** commit real `SUPABASE_DB_URL` passwords or Supabase **service_role** / **anon** keys.
- Set secrets in **Railway** → service → Variables and (if used) **GitHub** → repository secrets for Actions.
"""

    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(md, encoding="utf-8")
    print(f"Wrote {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
