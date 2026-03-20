# AussiePropertyData

Australian property investment analytics SaaS — Victorian suburb-level price history, rental yield, demographic trends, and investment scoring.

## Tech Stack

- **Database**: PostgreSQL on Supabase
- **API**: FastAPI (Python 3.12)
- **Deploy**: Railway / GitHub Actions

**Deploy / link from your machine:** [docs/CLI_DEPLOY.md](docs/CLI_DEPLOY.md) (`railway up`, `supabase link`).

## Setup

1. Create a Supabase project and run `schema/schema.sql` to create the database schema.

2. Set environment variables:
   ```env
   # Required
   SUPABASE_DB_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

   # Production (Railway)
   ENV=production
   # Comma-separated browser origins allowed to call the API
   CORS_ORIGINS=http://localhost:5173,https://aussiepropertydata.lovable.app,https://9d387518-e185-4a1e-aecf-4e7c4d6e163b.lovableproject.com
   ```

3. Place `master_dataset.json` in the project root with 747 suburbs pre-joined. Then seed:
   ```bash
   python -m ingestion.seed_master
   python -m ingestion.seed_price_history
   ```

4. Run the API locally:
   ```bash
   uvicorn api.main:app --reload
   ```

## Testing

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v
```

Covers VPSR XLS parsing, DFFH rent extraction, and quarterly suburb name resolution (no database required).

**Verify ingestion from your computer** (tests + live catalogue checks; add `--write-db` + `SUPABASE_DB_URL` for a full DB run): see [docs/AUTOMATION.md](docs/AUTOMATION.md) or run `python3 scripts/verify_ingestion_local.py`.

## Deployment reference (CLI)

From the repo root (with [Railway CLI](https://docs.railway.com/guides/cli) linked and [Supabase CLI](https://supabase.com/docs/guides/cli) logged in):

```bash
python3 scripts/update_deployment_docs.py
```

Writes **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** with Railway service IDs, public API URL, and Supabase project ref — **passwords and keys are redacted**. Use **`.env.example`** as a template for local secrets.

## API Endpoints

- `GET /health` — Liveness (no database; use for load balancers)
- `GET /health/ready` — Readiness (`SELECT 1` against Supabase; returns 503 if DB unreachable)
- `GET /suburbs/` — List suburbs (with filters)
- `GET /suburbs/top?profile=balanced` — Top suburbs by profile
- `GET /suburbs/search?q=...` — Fuzzy suburb search
- `POST /suburbs/filter` — Full investor screener
- `GET /suburbs/{name}` — Full suburb profile
- `GET /suburbs/{name}/history` — Price history
- `GET /suburbs/{name}/compare?with_suburb=...` — Compare two suburbs
- `GET /suburbs/{name}/similar` — Similar suburbs
- `GET /market/summary` — Victoria-wide stats

## Data Ingestion

Verified sources, URLs, and quarterly workflow: **[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)**.

- **VPSR houses**: `python -m ingestion.vpsr_houses` (quarterly). Optional: `VPSR_HOUSES_XLS` / `VPSR_LOCAL_XLS` for a local `.xls`, or **`VPSR_HOUSES_URL`** for any HTTPS URL (used in GitHub Actions when `land.vic` returns 403).
- **VPSR units**: `python -m ingestion.vpsr_units` (quarterly). Optional: `VPSR_UNITS_XLS` or **`VPSR_UNITS_URL`**.
- **DFFH rental**: `python -m ingestion.dffh_rental` (quarterly). Optional: `DFFH_RENTAL_XLSX`.
- **Recompute scores** after loads: `python -m ingestion.recompute_scores`

**Automation:** [docs/AUTOMATION.md](docs/AUTOMATION.md) — scheduled GitHub Actions poll the catalogues (exact Vic release dates aren’t fixed). Set `SUPABASE_DB_URL` in repo secrets. If VPSR downloads get **403** from the runner, run **`python3 scripts/publish_vpsr_mirror.py`** (then set **`VPSR_HOUSES_URL`** / **`VPSR_UNITS_URL`** to GitHub Release URLs) — see the “VPSR mirror for CI” section in AUTOMATION.md — or use local `VPSR_*_XLS` paths as in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).
