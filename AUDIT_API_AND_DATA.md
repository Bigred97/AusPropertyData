# API & Data Sources — Audit (Cleaning & Optimisation)

**Project:** AussiePropertyData  
**API:** https://auspropertydata-production.up.railway.app

---

## 1. Data quality & cleaning

### 1.1 Quarterly file vs master suburb list
- **`quarterly_q2_2025.json`** has **753** locality keys; **`master_dataset.json`** has **747** suburbs.
- **~59** quarterly keys do **not** match a `suburbs` row (e.g. `ALTONA EAST`, `CLAYTON NORTH`, compound/split VPSR names). `seed_quarterly` runs `UPDATE ... WHERE suburb = $1` → **no row updated** for those keys (silent no-op).
- **~53** master suburbs have **no** quarterly row in the JSON.

**Recommendation:**  
- Build a **mapping table** (VPSR locality → canonical `suburbs.suburb`) or a one-off script that reports `UPDATE 0` keys for manual review.  
- Optionally log skipped keys during seed.

### 1.2 Yield coverage (~197 / 747)
- **`rent_yield_update.json`** aligns with DFFH-style coverage; this is a **dataset limit**, not a bug.
- **`gross_yield`** in JSON should stay consistent with **house** median (`price_2023`) for 3br rent. If any row used **unit** price in the denominator, yields would be wrong — spot-check a few suburbs against your spreadsheet.

### 1.3 Investment score coverage (~197 scored)
- `inv_score` is **NULL** when `gross_yield` or `growth_10yr` is missing (by design).
- **Improving score coverage** requires more yield (or a model that scores without yield — product decision).

### 1.4 Duplicate / divergent business logic
- **`compute_inv_profile`** exists in `ingestion/seed_master.py`.
- **`compute_profile` + `compute_score`** in `ingestion/recompute_scores.py`.
- **`compute_inv_score`** in `api/scoring.py` (same formula as recompute, but **not imported** by recompute).

**Risk:** Rules drift between seed and recompute.

**Recommendation:**  
- Single module e.g. `ingestion/scoring.py` (or reuse `api/scoring.py` from ingestion) and import from `seed_master`, `recompute_scores`, and tests.

### 1.5 `inv_profile` vs `balanced` top list
- `GET /suburbs/top?profile=balanced` sorts by **`inv_score`**. Suburbs with **NULL** `inv_score` are ordered **NULLS LAST**, so the “top” balanced list is really “highest inv_score among those that have one,” not a separate “balanced” segment.
- **`general`** profile exists in DB but is **not** in the filter `Literal` on `POST /suburbs/filter` (only the four named profiles).

**Recommendation:**  
- Document this behaviour for the frontend, or change “balanced” ranking to a dedicated rule (e.g. filter `inv_profile = 'balanced'` then sort).

---

## 2. API behaviour & security

### 2.1 `SELECT *` on suburb detail / compare
- Returns **all** columns (including many annual price columns). Payload is larger than needed for a minimal “card” view.

**Recommendation:**  
- For list endpoints you already project columns — good. For detail, either keep `SELECT *` for simplicity or add a **field set** / GraphQL-style later if bandwidth matters.

### 2.2 SQL injection
- **`sort_by`** / **`sort_col`** are constrained to **allowlists** — safe.
- **`filter_suburbs`** builds dynamic `WHERE` with numbered params — safe.

### 2.3 CORS
- **`allow_origins=["*"]`** is convenient for Lovable; for production, restrict to known front-end origins.

### 2.4 Missing env var
- If `SUPABASE_DB_URL` is unset, you get **KeyError** → 500.  

**Recommendation:**  
- At startup, check env and fail fast with a clear message, or return 503 with “misconfigured” on DB errors.

### 2.5 Pydantic v2
- `class Config` on models is legacy; prefer `model_config = ConfigDict(...)`.

---

## 3. Performance & database

### 3.1 `recompute_scores.py`
- **747 sequential `UPDATE`s** — works but slow on cold connections.

**Recommendation:**  
- Single `UPDATE ... FROM (VALUES ...)` batch, or `executemany`, or temp table + join update.

### 3.2 Seed scripts (`seed_unit_prices`, `seed_quarterly`, `seed_rent_yield`)
- Per-row `UPDATE` — same as above; acceptable at 400–700 rows, but **`executemany`** or COPY would be faster.

### 3.3 Indexes
- Existing indexes match common filters (`price_2023`, `gross_yield`, `inv_score`, `irsd_decile`, `postcode`, `is_metro`, `inv_profile`, trigram on `suburb`).  
- **Optional:** composite index for frequent screener patterns, e.g. `(is_metro, price_2023, gross_yield)` — only after measuring slow queries in Supabase.

### 3.4 Connection pool
- **`statement_cache_size=0`** is correct for **transaction** pooler; if you move to **direct** Postgres on Railway, you can re-enable statement cache for a small latency win.

### 3.5 Market summary
- Full table scan aggregates — fine for **747** rows. If the table grows 10×, consider **materialized view** + refresh on ingest.

---

## 4. Operational / repo hygiene

| Item | Suggestion |
|------|------------|
| **GitHub Actions** | Ensure `SUPABASE_DB_URL` secret matches pooler/direct URL your scripts expect. |
| **Ingestion order** | Document: `seed_rent_yield` → `seed_unit_prices` → `seed_quarterly` → `recompute_scores` (or your chosen order). |
| **Secrets** | Never commit `master_dataset.json` with sensitive data; `.gitignore` large dumps if needed. |
| **OpenAPI** | `/docs` exposes schema — fine for internal use; consider disabling in production if you want to reduce surface. |

---

## 5. Priority summary

| Priority | Item |
|----------|------|
| **High** | Unify scoring/profile logic in one module |
| **High** | Document or map quarterly locality names → canonical suburbs |
| **Medium** | Batch `recompute_scores` updates |
| **Medium** | Tighten CORS + clearer error if DB URL missing |
| **Low** | Pydantic `model_config` migration |
| **Low** | Composite indexes after query profiling |

---

## 6. Nothing urgent for correctness

- Endpoints behave as designed; validation and allowlists are sound.  
- Main **limitations** are **data coverage** (yield, quarterly name mismatches) and **maintainability** (duplicated scoring), not broken API behaviour.
