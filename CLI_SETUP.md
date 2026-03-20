# Supabase CLI setup — complete

Run these commands in order. Replace `YOUR_STRONG_PASSWORD` and `YOUR_ORG_ID` with your values.

## 1. Install Supabase CLI

```bash
brew install supabase/tap/supabase
```

## 2. Login (opens browser)

```bash
supabase login
```

Sign in with your Supabase account in the browser.

## 3. Get your org ID

```bash
supabase orgs list
```

Copy the `id` from the output (or use the first org).

## 4. Create the project

```bash
supabase projects create aussiepropertydata \
  --org-id YOUR_ORG_ID \
  --region ap-southeast-2 \
  --db-password YOUR_STRONG_PASSWORD
```

## 5. Get the project ref

```bash
supabase projects list
```

Copy the project `id` (ref) for `aussiepropertydata` — looks like `abcdefghijklmnop`.

## 6. Push the schema

**Get your connection string** from [Supabase Dashboard](https://supabase.com/dashboard) → your project → **Connect** → **Session mode** (or URI). New projects need ~2 min to provision.

```bash
cd /Users/harry/Desktop/AusPropertyData
# Option A: Use connection string from dashboard
export SUPABASE_DB_URL="postgresql://postgres.[REF]:[PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres"
./scripts/setup_supabase.sh

# Option B: Run schema + seed manually
psql "$SUPABASE_DB_URL" -f schema/schema.sql
python -m ingestion.seed_master
```

## 7. Set env and seed

```bash
export SUPABASE_DB_URL="postgresql://postgres:YOUR_STRONG_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres"
python -m ingestion.seed_master
```

Expected: `Seeded 747/747 suburbs.`

## 8. Run API and test

```bash
uvicorn api.main:app --reload
```

Then hit:
- http://localhost:8000/health
- http://localhost:8000/market/summary
- http://localhost:8000/suburbs/ABBOTSFORD
- http://localhost:8000/suburbs/top?profile=yield_hunter&limit=5
- http://localhost:8000/suburbs/CRANBOURNE/history
- http://localhost:8000/suburbs/MORWELL/compare?with_suburb=SHEPPARTON

## 9. Test screener

```bash
curl -X POST http://localhost:8000/suburbs/filter \
  -H "Content-Type: application/json" \
  -d '{"min_yield": 4.0, "max_price": 700000, "is_metro": true, "limit": 5}'
```

Expected: Broadmeadows and Craigieburn in top results.

## 10. Deploy to Railway

```bash
railway login
railway init
railway up
railway variables set SUPABASE_DB_URL="postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres"
```

**Important:** Use the **direct** connection (port 5432, `db.xxx.supabase.co`), not the pooler. The pooler (port 6543) is for serverless; FastAPI with asyncpg needs the direct connection for persistent connections.

---

**Connection string formats:**
- **Railway / persistent apps:** `postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres`
- **Serverless / edge:** pooler URL with port 6543
