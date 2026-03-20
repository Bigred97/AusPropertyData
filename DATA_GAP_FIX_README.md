# Backend Data Gap Fix — Run Instructions

## Source files required

Place these JSON files in the project root **before** running the seed scripts:

1. **`unit_prices.json`** — Format:
   ```json
   [{"suburb": "ABBOTSFORD", "unit_price_2023": 530000}, ...]
   ```

2. **`quarterly_q2_2025.json`** — Format:
   ```json
   {"ABBOTSFORD": {"price_q2_2025": 1295000, "sales_q2_2025": 21}, ...}
   ```

## Run order

```bash
cd /Users/harry/Desktop/AusPropertyData
export SUPABASE_DB_URL="postgresql://postgres.ksmumnnyioxcxutodiax:YOUR_PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"

# 1. Migration (columns already exist in schema; run if needed)
psql $SUPABASE_DB_URL -f schema/migrations/001_add_unit_quarterly.sql

# 2. Load data (requires unit_prices.json and quarterly_q2_2025.json)
python -m ingestion.seed_unit_prices
python -m ingestion.seed_quarterly

# 3. Recompute scores (run after any data update)
python -m ingestion.recompute_scores

# 4. Redeploy API
railway up
```

## Verification

```bash
# Unit prices
curl "https://auspropertydata-production.up.railway.app/suburbs/ABBOTSFORD" | python3 -m json.tool | grep unit_price_2023

# Quarterly
curl "https://auspropertydata-production.up.railway.app/suburbs/CRANBOURNE" | python3 -m json.tool | grep -E "price_q2|sales_volume"

# Market summary
curl "https://auspropertydata-production.up.railway.app/market/summary"
```
