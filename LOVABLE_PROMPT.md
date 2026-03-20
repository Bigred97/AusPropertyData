# Lovable / Frontend Prompt — AussiePropertyData

**Frontend (live):** [aussiepropertydata.lovable.app](https://aussiepropertydata.lovable.app)

**Replace any placeholder with this live API URL:**

All data comes from this REST API: `https://auspropertydata-production.up.railway.app`

In your `api.ts` (or API client config), set:

```typescript
const API_BASE_URL = "https://auspropertydata-production.up.railway.app";
```

---

## API Endpoints

- `GET /health` — Health check
- `GET /market/summary` — Victoria-wide stats
- `GET /suburbs/` — List suburbs (filters: is_metro, min_price, max_price, limit, offset, sort_by, sort_dir)
- `GET /suburbs/top?profile=yield_hunter|growth_chaser|gentrification|balanced&limit=10` — Pre-built ranked lists
- `GET /suburbs/search?q=...&limit=10` — Fuzzy suburb search
- `POST /suburbs/filter` — Full screener (JSON body with min_yield, max_price, is_metro, etc.)
- `GET /suburbs/{name}` — Full suburb profile
- `GET /suburbs/{name}/history` — 11-year price series
- `GET /suburbs/{name}/compare?with_suburb=...` — Compare two suburbs
- `GET /suburbs/{name}/similar?limit=5` — Similar suburbs
- `GET /suburbs/export?...` — CSV download (same filter query params as screener; `limit` default 500, max 747). Columns include `score_label` and `summary` when those DB columns exist (after migration + `python -m ingestion.generate_summaries` for summaries).
- `GET /calculators/stamp-duty?price=...&first_home_buyer=true|false`
- `GET /calculators/yield?purchase_price=...&weekly_rent=...`

---

## Response shape

List endpoints (`GET /suburbs/`, `/top`, `/search`, etc.) return a **JSON array** directly, e.g. `[{ "suburb": "...", ... }, ...]`, not `{ "data": [...] }`. If the UI is empty, check that you are not reading `.data` on the parsed JSON.

`GET /market/summary` includes a nested **`benchmarks`** object (`vic_avg_yield`, `vic_avg_growth_10yr`, `vic_avg_price_2023`, `vic_median_irsd_decile`, `vic_pct_suburbs_doubled`).

Suburb detail (`GET /suburbs/{name}`) adds **`summary`**, **`score_label`**, and comparison strings **`growth_vs_avg`**, **`yield_vs_avg`**, **`price_vs_avg`**. List/screener rows include **`summary`** and **`score_label`** (nullable until backfilled).

## CORS

Production allows `localhost:5173`, the default production Lovable host, **any** `https://*.lovable.app` origin, and **any** `https://*.lovableproject.com` origin (Lovable preview IDs). You can still add explicit origins via Railway env `CORS_ORIGINS` (comma-separated).
