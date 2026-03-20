# AussiePropertyData — Backend Data Gap Fix

## Context

The backend API is deployed at `https://auspropertydata-production.up.railway.app`.
The database is Postgres on Supabase. The project is at `/Users/harry/Desktop/AusPropertyData`.

Three data gaps need fixing. All source data files are already downloaded and
provided as JSON files in the project root. Do not re-download anything.

---

## What to fix — 3 tasks in order

### Task 1: Load unit prices (0 → 419 suburbs)

**Source file:** `unit_prices.json` in project root.

**Format:**
```json
[
  {"suburb": "ABBOTSFORD", "unit_price_2023": 530000},
  {"suburb": "ABERFELDIE", "unit_price_2023": 750000}
]
```

**What to do:**

1. Add `unit_price_2023 INTEGER` column to the `suburbs` table if it doesn't
   already exist:
   ```sql
   ALTER TABLE suburbs ADD COLUMN IF NOT EXISTS unit_price_2023 INTEGER;
   ```

2. Create `ingestion/seed_unit_prices.py`:

```python
"""Load unit prices from unit_prices.json into suburbs table."""
import json, asyncio, asyncpg, os

async def seed():
    conn = await asyncpg.connect(os.environ["SUPABASE_DB_URL"])
    with open("unit_prices.json") as f:
        records = json.load(f)

    updated = 0
    for r in records:
        result = await conn.execute("""
            UPDATE suburbs
            SET unit_price_2023 = $2, data_updated_at = NOW()
            WHERE suburb = $1
        """, r["suburb"], r["unit_price_2023"])
        if result == "UPDATE 1":
            updated += 1

    await conn.close()
    print(f"Updated unit prices for {updated}/{len(records)} suburbs")

asyncio.run(seed())
```

3. Run it:
```bash
python -m ingestion.seed_unit_prices
```

Expected: `Updated unit prices for 419/419 suburbs`

4. Verify:
```bash
# Should return unit_price_2023: 530000
curl "https://auspropertydata-production.up.railway.app/suburbs/ABBOTSFORD" | python3 -m json.tool | grep unit
```

---

### Task 2: Load Q2 2025 prices + sales volume (694 suburbs)

**Source file:** `quarterly_q2_2025.json` in project root.

**Format:**
```json
{
  "ABBOTSFORD": {"price_q2_2025": 1295000, "sales_q2_2025": 21},
  "CRANBOURNE": {"price_q2_2025": 713500, "sales_q2_2025": 103}
}
```

**What to do:**

1. Add columns to `suburbs` table if they don't exist:
```sql
ALTER TABLE suburbs ADD COLUMN IF NOT EXISTS price_q2_2025 INTEGER;
ALTER TABLE suburbs ADD COLUMN IF NOT EXISTS sales_volume_q2_2025 INTEGER;
```

2. Create `ingestion/seed_quarterly.py`:

```python
"""Load Q2 2025 quarterly prices and sales volume."""
import json, asyncio, asyncpg, os

async def seed():
    conn = await asyncpg.connect(os.environ["SUPABASE_DB_URL"])
    with open("quarterly_q2_2025.json") as f:
        records = json.load(f)

    updated = 0
    for suburb, data in records.items():
        price = data.get("price_q2_2025")
        sales = data.get("sales_q2_2025")
        if not price:
            continue
        result = await conn.execute("""
            UPDATE suburbs
            SET price_q2_2025 = $2,
                sales_volume_q2_2025 = $3,
                data_updated_at = NOW()
            WHERE suburb = $1
        """, suburb, price, sales)
        if result == "UPDATE 1":
            updated += 1

    await conn.close()
    print(f"Updated quarterly data for {updated}/{len(records)} suburbs")

asyncio.run(seed())
```

3. Run it:
```bash
python -m ingestion.seed_quarterly
```

Expected: `Updated quarterly data for ~694 suburbs`

4. Verify — Cranbourne should show 103 sales last quarter:
```bash
curl "https://auspropertydata-production.up.railway.app/suburbs/CRANBOURNE" | python3 -m json.tool | grep -E "price_q2|sales_volume"
```

---

### Task 3: Recompute investment scores (16% → ~55%)

Now that unit prices are loaded, recalculate `inv_score` and `inv_profile`
for all suburbs that have the required signals. The score formula uses:
yield + growth + young families % + train distance + SEIFA + pop growth.

Many suburbs now have more complete data. Update the scoring run.

Create `ingestion/recompute_scores.py`:

```python
"""
Recompute investment score and profile for all suburbs.
Run after any data update that changes signals used in the score.
"""
import asyncio, asyncpg, os, math

def compute_score(r: dict) -> float | None:
    """
    Composite investment score. Higher = better.
    Requires at minimum: gross_yield and growth_10yr.
    """
    if not r.get("gross_yield") or not r.get("growth_10yr"):
        return None

    yield_     = float(r.get("gross_yield") or 0)
    growth     = float(r.get("growth_10yr") or 0)
    yf_pct     = float(r.get("pct_young_families") or 20)
    dist       = float(r.get("dist_to_station_km") or 10)
    irsd       = int(r.get("irsd_decile") or 5)
    pop36      = min(float(r.get("pop_growth_to_2036_pct") or 0), 200)

    seifa_adj  = (irsd - 5) * 1.5
    pop_signal = pop36 * 0.15

    return round(
        (yield_ * 15) +
        (growth * 0.3) +
        (yf_pct * 0.5) -
        (dist * 2) +
        seifa_adj +
        pop_signal,
        2
    )

def compute_profile(r: dict) -> str:
    yield_     = float(r.get("gross_yield") or 0)
    growth     = float(r.get("growth_10yr") or 0)
    irsd       = int(r.get("irsd_decile") or 5)
    yf         = float(r.get("pct_young_families") or 0)
    pop36      = float(r.get("pop_growth_to_2036_pct") or 0)
    price      = int(r.get("price_2023") or 999999)

    if yield_ >= 4.5:
        return "yield_hunter"
    elif pop36 >= 80 and price < 800000:
        return "growth_chaser"
    elif irsd <= 3 and yf >= 33 and growth >= 70:
        return "gentrification"
    elif yield_ >= 3.5 and growth >= 80 and pop36 >= 20:
        return "balanced"
    return "general"

async def recompute():
    conn = await asyncpg.connect(os.environ["SUPABASE_DB_URL"])

    # Fetch all suburbs with all scoring fields
    rows = await conn.fetch("""
        SELECT suburb, gross_yield, growth_10yr, pct_young_families,
               dist_to_station_km, irsd_decile, pop_growth_to_2036_pct,
               price_2023
        FROM suburbs
    """)

    scored = 0
    profiled = 0

    for row in rows:
        r = dict(row)
        score = compute_score(r)
        profile = compute_profile(r)

        await conn.execute("""
            UPDATE suburbs
            SET inv_score = $2, inv_profile = $3, data_updated_at = NOW()
            WHERE suburb = $1
        """, r["suburb"], score, profile)

        if score:
            scored += 1
        profiled += 1

    await conn.close()
    print(f"Scores computed for {scored}/{profiled} suburbs")
    print(f"Profiles assigned for {profiled} suburbs")

asyncio.run(recompute())
```

Run it:
```bash
python -m ingestion.recompute_scores
```

Expected: `Scores computed for ~400+ suburbs` (up from 123)

---

### Task 4: Add new fields to the API response

The API needs to return the new fields. Update `api/models/suburb.py` to add:

```python
unit_price_2023: Optional[int]
price_q2_2025: Optional[int]
sales_volume_q2_2025: Optional[int]
```

These are already in the `suburbs` table after running the migration above.
No other API changes needed — the `SELECT *` in `GET /suburbs/:name` will
automatically include them.

Also update `api/routers/market.py` to expose sales volume in the summary:

In `market_summary()`, add to the SQL query:
```sql
ROUND(AVG(sales_volume_q2_2025)::numeric, 0) as avg_quarterly_sales
```

---

### Task 5: Update the GitHub Actions cron

Add the new seed scripts to `.github/workflows/update_data.yml` so they run
after the quarterly VPSR ingestion:

```yaml
- name: Recompute investment scores
  env:
    SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
  run: python -m ingestion.recompute_scores
```

Add this step after the existing `vpsr_houses` and `dffh_rental` steps.

---

## Run order

```bash
cd /Users/harry/Desktop/AusPropertyData
export SUPABASE_DB_URL="postgresql://postgres:YOUR_PASSWORD@db.ksmumnnyioxcxutodiax.supabase.co:5432/postgres"

# 1. Add new columns to DB
psql $SUPABASE_DB_URL -c "ALTER TABLE suburbs ADD COLUMN IF NOT EXISTS unit_price_2023 INTEGER;"
psql $SUPABASE_DB_URL -c "ALTER TABLE suburbs ADD COLUMN IF NOT EXISTS price_q2_2025 INTEGER;"
psql $SUPABASE_DB_URL -c "ALTER TABLE suburbs ADD COLUMN IF NOT EXISTS sales_volume_q2_2025 INTEGER;"

# 2. Load data
python -m ingestion.seed_unit_prices
python -m ingestion.seed_quarterly
python -m ingestion.recompute_scores

# 3. Redeploy API to Railway
railway up
```

---

## Definition of done

Run these checks — all must pass:

```bash
# Unit prices loaded
curl ".../suburbs/ABBOTSFORD" | python3 -m json.tool | grep unit_price_2023
# Expected: "unit_price_2023": 530000

# Quarterly price + sales loaded
curl ".../suburbs/CRANBOURNE" | python3 -m json.tool | grep -E "price_q2|sales_volume"
# Expected: "price_q2_2025": 713500, "sales_volume_q2_2025": 103

# Investment score improved
curl ".../suburbs/top?profile=balanced&limit=3"
# Expected: returns 3 suburbs with inv_score values

# Market summary
curl ".../market/summary" | python3 -m json.tool
# Expected: all fields populated with real numbers

# Verify score count in DB (run in Supabase SQL editor)
# SELECT COUNT(*) FROM suburbs WHERE inv_score IS NOT NULL;
# Expected: 400+
```

---

## What this does NOT fix (and why)

**Yield coverage stays at 197/747.** The DFFH rental report only covers
~200 suburb groupings across Victoria — that is the complete dataset.
There are no more suburbs to extract. To get yield for more suburbs
would require a paid data source (SQM Research API) or scraping REA/Domain
which carries legal risk. This is a V2 commercial decision, not a bug.

**Do not attempt to scrape any property portal or paid data source.**
