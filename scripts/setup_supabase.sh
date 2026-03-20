#!/bin/bash
# Supabase CLI setup — run after: supabase login
# Usage: SUPABASE_DB_PASSWORD=yourpassword ./scripts/setup_supabase.sh
# Or with connection string from dashboard: SUPABASE_DB_URL="postgresql://..." ./scripts/setup_supabase.sh

set -e
cd "$(dirname "$0")/.."

# Shortcut: if DB URL from dashboard, just push schema + seed
if [ -n "$SUPABASE_DB_URL" ]; then
  echo "=== Push schema ==="
  psql "$SUPABASE_DB_URL" -f schema/schema.sql
  echo "=== Seed suburbs ==="
  python3 -m ingestion.seed_master
  echo "=== Seed price history ==="
  python3 -m ingestion.seed_price_history
  echo "Done."
  exit 0
fi

DB_PASSWORD="${1:-$SUPABASE_DB_PASSWORD}"
[ -z "$DB_PASSWORD" ] && { echo "Usage: SUPABASE_DB_PASSWORD=x ./scripts/setup_supabase.sh"; exit 1; }

echo "=== 1. Get org ID ==="
ORG_ID=$(supabase orgs list --output json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'] if d else '')" 2>/dev/null)
[ -z "$ORG_ID" ] && { echo "Run: supabase orgs list"; read -p "Paste org ID: " ORG_ID; }

echo "=== 2. Create project ==="
supabase projects create aussiepropertydata --org-id "$ORG_ID" --region ap-southeast-2 --db-password "$DB_PASSWORD" 2>/dev/null || echo "(project may exist)"

echo "=== 3. Get project ref ==="
PROJECT_REF=$(supabase projects list 2>/dev/null | grep aussiepropertydata | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $3); print $3}')
[ -z "$PROJECT_REF" ] && { echo "Run: supabase projects list"; read -p "Paste project ref: " PROJECT_REF; }
echo "Project ref: $PROJECT_REF"

# Use SUPABASE_DB_URL if set (from dashboard), else build from project ref
if [ -n "$SUPABASE_DB_URL" ]; then
  DB_URL="$SUPABASE_DB_URL"
  echo "Using SUPABASE_DB_URL from env"
else
  # Pooler (IPv4-compatible; Sydney uses aws-1)
  DB_URL="postgresql://postgres.${PROJECT_REF}:${DB_PASSWORD}@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"
fi
echo "DB URL: ${DB_URL//:[^:@]*@/:****@}"

echo "=== 4. Wait for DB (new projects need ~2 min) ==="
for i in 1 2 3 4 5 6; do
  if psql "$DB_URL" -c "SELECT 1" 2>/dev/null; then break; fi
  echo "  Attempt $i/6: waiting 30s..."
  sleep 30
done

echo "=== 5. Push schema ==="
psql "$DB_URL" -f schema/schema.sql

echo "=== 6. Seed suburbs ==="
export SUPABASE_DB_URL="$DB_URL"
python3 -m ingestion.seed_master

echo "=== 7. Seed price history ==="
python3 -m ingestion.seed_price_history

echo ""
echo "Done. export SUPABASE_DB_URL=\"$DB_URL\""
