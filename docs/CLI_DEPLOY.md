# CLI: Railway + Supabase

## Railway (deploy the API)

Prerequisites: [Railway CLI](https://docs.railway.com/guides/cli) installed and logged in (`railway login`).

```bash
cd /path/to/AusPropertyData
railway link   # once per machine: select project AusPropertyData, service AusPropertyData
railway up --ci    # upload, build, stream logs until deploy + healthcheck finish
# or: railway up -d   # fire-and-forget
```

Ensure **Railway → Variables** includes a valid `SUPABASE_DB_URL` (and `CORS_ORIGINS` if needed). The API will not pass `/health` in production if the DB pool cannot start.

If deploy fails with **“network process”** or the app won’t start, check for **typos in variables** (merged CORS URLs, missing `@` in the DB URI): [RAILWAY_ENV.md](RAILWAY_ENV.md).

The API **does not open Postgres during process startup**. **`GET /health`** is liveness only (always fast). The DB pool (plus schema probe) is created on the **first** DB-backed request. Railway’s **`healthcheckPath`** should stay **`/health`** so deploys are not blocked while Postgres warms up. Use **`GET /health/ready`** manually or for a stricter probe to verify Supabase connectivity.

## Supabase (link project for CLI)

Prerequisites: [Supabase CLI](https://supabase.com/docs/guides/cli) installed and logged in (`supabase login`).

This repo includes `supabase/config.toml` from `supabase init`. **Link** matches the CLI to your hosted project (ref `ksmumnnyioxcxutodiax`):

```bash
cd /path/to/AusPropertyData
# Password = database password from the Supabase dashboard (not the anon key)
supabase link --project-ref ksmumnnyioxcxutodiax -p "YOUR_DB_PASSWORD" --yes
```

Check: `supabase projects list` should show **●** under LINKED.

### Migrations

Canonical SQL for this app still lives under **`schema/`** and **`schema/migrations/`** (applied manually or via `psql` in the past). The Supabase CLI’s **`supabase db push`** expects versioned files under **`supabase/migrations/`** in `YYYYMMDDHHMMSS_name.sql` form. If you adopt that workflow, copy or port changes there and run:

```bash
supabase db push --linked --yes
```

Use **`supabase db push --dry-run`** first to see what would run.
