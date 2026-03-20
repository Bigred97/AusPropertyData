# Automated ingestion schedule

Victorian agencies **do not publish on a fixed calendar day**. VPSR (houses/units) is typically **~3 months** after quarter end; DFFH rental **~2–3 months**. See the release table in [DATA_SOURCES.md](DATA_SOURCES.md).

Because of that, **exact-interval automation is not possible**. The practical approach is **scheduled polling**: run ingestion on a cadence so that when a new file appears on the data.vic catalogue, the job picks it up within about a week.

## What runs in CI

Workflow: [`.github/workflows/update_data.yml`](../.github/workflows/update_data.yml)

| Trigger | Purpose |
|--------|---------|
| **Weekly** (Mon 22:00 UTC) | Main poll — Vic release dates vary, so we check often |
| **Monthly 15th** (22:00 UTC) | Extra run when DFFH often publishes |
| **`workflow_dispatch`** | Run manually after you confirm a new file on the catalogue |

Steps (in order): `dffh_rental` → `vpsr_houses` → `vpsr_units` → `recompute_scores`.

DFFH runs first because **`dffh.vic.gov.au` downloads usually succeed from GitHub Actions**, while **`land.vic.gov.au` often returns 403** to datacentre IPs. If the VPSR steps fail in CI, yields may still update for that run; fix VPSR by mirroring (below) or run houses/units locally with `VPSR_*_XLS`.

## GitHub secrets

| Secret | Required |
|--------|----------|
| `SUPABASE_DB_URL` | Yes — use the URI from Supabase (transaction pooler `:6543` is fine for CI; **direct** `db.*.supabase.co:5432` often behaves better for local asyncpg — see `.env.example`) |
| `VPSR_HOUSES_URL` | No — HTTPS URL to the house `.xls` if `land.vic` blocks the runner (e.g. raw file on a release asset or your own mirror) |
| `VPSR_UNITS_URL` | No — same for the unit `.xls` |
| `DFFH_RENTAL_URL` | No — HTTPS mirror of the DFFH `.xlsx` when `dffh.vic.gov.au` stalls on the runner (same pattern as VPSR mirrors) |
| `SLACK_WEBHOOK` | No — if set, failed runs post a message |

## VPSR mirror for CI (fixes land.vic 403 on GitHub)

Data Vic’s CKAN API still points file URLs at **`land.vic.gov.au`**, which often **403s datacentre IPs**. The reliable fix is to host copies of the official `.xls` files somewhere Actions can GET (e.g. **GitHub Release assets**).

1. From the repo root:
   ```bash
   python3 -m pip install -r requirements.txt   # use this if `pip` is not on your PATH (common on macOS)
   python3 scripts/publish_vpsr_mirror.py --out mirror
   ```
   If that fails with **403**, Land Vic is blocking scripted GET on your network too — use **“Go to Resource”** on the [house](https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-house-by-suburb) and [unit](https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-unit-by-suburb) catalogue pages, save both `.xls`, then:
   ```bash
   python3 scripts/publish_vpsr_mirror.py --houses-xls /path/to/median-house-....xls \
       --units-xls /path/to/median-unit-....xls --out mirror
   ```
2. Upload the two files to a **long-lived release tag** (example tag `vpsr-mirror`):
   ```bash
   gh release create vpsr-mirror --title "VPSR mirror for CI" --notes "See docs/AUTOMATION.md" || true
   gh release upload vpsr-mirror mirror/*.xls --clobber
   ```
   Or do both in one step:
   ```bash
   python3 scripts/publish_vpsr_mirror.py --gh-release vpsr-mirror
   ```
   If the printed URLs show `OWNER/REPO`, this folder may have no `git` remote — pass your repo explicitly:
   ```bash
   python3 scripts/publish_vpsr_mirror.py --repo YOUR_USER/AusPropertyData --gh-release vpsr-mirror ...
   ```
   **GitHub CLI** (`gh`) is required for `--gh-release`. On macOS: `brew install gh` then `gh auth login`. If you skip that, the script still copies files into `mirror/`; upload them manually on **GitHub → Releases** (create tag `vpsr-mirror`, attach both `.xls`).

   If the project folder has **no `.git`**, `gh release …` must know the repo: pass **`--repo YourUser/YourRepo`** (your real names — not the literal text `YOUR_GITHUB_USER`).

   **Private repos:** anonymous `GET` of `releases/download/...` URLs returns 404. Either make the mirror repo **public** (the XLS is CC-BY open data) or host files on a public URL (e.g. object storage).
3. In the repo **Settings → Secrets → Actions**, set **`VPSR_HOUSES_URL`** and **`VPSR_UNITS_URL`** to the `releases/download/...` URLs the script prints (they look like  
   `https://github.com/OWNER/REPO/releases/download/vpsr-mirror/median-house-q2-2025.xls`).

Re-run the mirror script when a **new quarter** appears on the catalogue, then **`gh release upload ... --clobber`** (or `publish_vpsr_mirror.py --gh-release vpsr-mirror` again) so the same tag always serves the latest files; **update the secret values only if filenames change**.

## Limits

1. **`land.vic.gov.au` may still return 403** to some datacentre IPs. Ingestion sends a **CKAN catalogue `Referer`** plus browser-like headers; if it still fails, set GitHub secrets **`VPSR_HOUSES_URL`** / **`VPSR_UNITS_URL`** to stable HTTPS URLs (e.g. attach the official `.xls` to a **GitHub Release** and use the `raw.githubusercontent.com/...` link, or upload to cloud storage). Alternatively download in a browser and re-run locally with `VPSR_HOUSES_XLS` / `VPSR_UNITS_XLS` ([DATA_SOURCES.md](DATA_SOURCES.md)).
2. **Idempotency**: Re-running on the same catalogue file mostly re-writes the same values; safe to poll weekly.
3. **Schema columns**: House quarterly columns in DB may still be tied to a specific quarter in code — after a major VPSR format change, update ingestion and migrations as needed.

## Verify on your laptop (no GitHub)

From the repo root:

```bash
pip install -r requirements.txt
# optional: pip install -r requirements-dev.txt   # for pytest in phase 1
python3 scripts/verify_ingestion_local.py
```

Phase 1 runs **pytest** on parsers; phase 2 checks **data.vic catalogues** and probes **land.vic** download (403 on your network is OK — use `VPSR_HOUSES_XLS`).

End-to-end against Supabase (writes data):

```bash
export SUPABASE_DB_URL='postgresql://...'
python3 scripts/verify_ingestion_local.py --write-db
```

## Railway / other hosts

You can run the same commands on a cron job (Railway Cron, etc.) with the same env vars. GitHub Actions avoids hosting cost and keeps logs in one place.
