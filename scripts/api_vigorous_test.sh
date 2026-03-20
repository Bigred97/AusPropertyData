#!/usr/bin/env bash
# Vigorous production API checks — run from repo root: bash scripts/api_vigorous_test.sh
set -euo pipefail
BASE="${API_BASE_URL:-https://auspropertydata-production.up.railway.app}"
PASS=0
FAIL=0
fail() { echo "  FAIL: $*"; FAIL=$((FAIL+1)); }
pass() { echo "  OK:   $*"; PASS=$((PASS+1)); }

command -v jq >/dev/null 2>&1 || { echo "jq required"; exit 1; }

section() { echo ""; echo "=== $* ==="; }

http_code() {
  curl -sS -o /tmp/apitest_body.json -w "%{http_code}" "$@" || echo "000"
}

section "Health & latency"
code=$(http_code "$BASE/health")
if [[ "$code" == "200" ]] && jq -e '.status == "ok"' /tmp/apitest_body.json >/dev/null; then
  pass "/health 200 + status ok"
else
  fail "/health expected 200+ok got $code $(cat /tmp/apitest_body.json 2>/dev/null | head -c 200)"
fi

section "Market summary"
code=$(http_code "$BASE/market/summary")
if [[ "$code" == "200" ]]; then
  if jq -e '.total_suburbs > 100 and .avg_price != null and (.benchmarks | type == "object") and (.benchmarks.vic_avg_yield != null)' /tmp/apitest_body.json >/dev/null; then
    pass "/market/summary + benchmarks.vic_avg_yield"
  else
    fail "/market/summary bad JSON shape: $(head -c 300 /tmp/apitest_body.json)"
  fi
else
  fail "/market/summary HTTP $code"
fi

section "List suburbs + filters"
code=$(http_code "$BASE/suburbs/?limit=5")
[[ "$code" == "200" ]] && len=$(jq 'length' /tmp/apitest_body.json) || len=-1
if [[ "$len" -eq 5 ]] && jq -e '.[0] | has("suburb") and has("inv_score") and has("summary") and has("score_label")' /tmp/apitest_body.json >/dev/null; then
  pass "GET /suburbs/?limit=5 array + keys (summary, score_label)"
else
  fail "GET /suburbs/?limit=5 got code=$code len=$len"
fi

code=$(http_code "$BASE/suburbs/?is_metro=true&min_price=400000&max_price=900000&limit=10")
if [[ "$code" == "200" ]]; then
  bad=$(jq '[.[] | select(.is_metro != true or .price_2023 < 400000 or .price_2023 > 900000)] | length' /tmp/apitest_body.json)
  if [[ "$bad" == "0" ]]; then
    pass "metro + price band filters consistent"
  else
    fail "filter rows violate constraints count=$bad"
  fi
else
  fail "filtered list HTTP $code"
fi

section "Top profiles (all 4)"
for p in yield_hunter growth_chaser gentrification balanced; do
  code=$(http_code "$BASE/suburbs/top?profile=$p&limit=5")
  if [[ "$code" == "200" ]] && [[ "$(jq 'length' /tmp/apitest_body.json)" -eq 5 ]]; then
    pass "/suburbs/top profile=$p"
  else
    fail "/suburbs/top profile=$p code=$code"
  fi
done

section "Search"
code=$(http_code "$BASE/suburbs/search?q=cran&limit=5")
if [[ "$code" == "200" ]] && [[ "$(jq 'length' /tmp/apitest_body.json)" -ge 1 ]]; then
  pass "/suburbs/search?q=cran"
else
  fail "/suburbs/search cran code=$code body=$(head -c 200 /tmp/apitest_body.json)"
fi

code=$(http_code "$BASE/suburbs/search?q=a")
if [[ "$code" == "422" ]]; then
  pass "/suburbs/search short q -> 422"
else
  fail "expected 422 for short search, got $code"
fi

section "POST /suburbs/filter"
code=$(curl -sS -o /tmp/apitest_body.json -w "%{http_code}" -X POST "$BASE/suburbs/filter" \
  -H "Content-Type: application/json" \
  -d '{"min_yield":4,"max_price":800000,"is_metro":true,"limit":8,"sort_by":"gross_yield","sort_dir":"desc"}')
if [[ "$code" == "200" ]]; then
  n=$(jq 'length' /tmp/apitest_body.json)
  if [[ "$n" -ge 1 ]] && [[ "$n" -le 8 ]]; then
    bad=$(jq '[.[] | select(.gross_yield < 4 or .price_2023 > 800000 or .is_metro != true)] | length' /tmp/apitest_body.json)
    [[ "$bad" == "0" ]] && pass "POST filter metro yield price ($n rows)" || fail "POST filter inconsistent rows"
  else
    fail "POST filter row count $n"
  fi
else
  fail "POST /suburbs/filter HTTP $code $(head -c 200 /tmp/apitest_body.json)"
fi

section "Detail, history, compare, similar"
code=$(http_code "$BASE/suburbs/ABBOTSFORD")
if [[ "$code" == "200" ]] && jq -e '.suburb == "ABBOTSFORD" and .price_2023 != null and has("growth_vs_avg") and has("yield_vs_avg") and has("price_vs_avg")' /tmp/apitest_body.json >/dev/null; then
  pass "GET /suburbs/ABBOTSFORD + vs_avg fields"
else
  fail "ABBOTSFORD detail $code"
fi

code=$(http_code "$BASE/suburbs/ZZZNOTFOUND999")
[[ "$code" == "404" ]] && pass "unknown suburb 404" || fail "expected 404 got $code"

code=$(http_code "$BASE/suburbs/CRANBOURNE/history")
if [[ "$code" == "200" ]]; then
  n=$(jq 'length' /tmp/apitest_body.json)
  if [[ "$n" -ge 5 ]] && jq -e '.[0] | has("year") and has("median_price")' /tmp/apitest_body.json >/dev/null; then
    pass "CRANBOURNE history ($n points)"
  else
    fail "history shape wrong"
  fi
else
  fail "history HTTP $code"
fi

code=$(http_code "$BASE/suburbs/ZZZNONE/history")
[[ "$code" == "404" ]] && pass "no history 404" || fail "history 404 expected got $code"

code=$(http_code "$BASE/suburbs/CRANBOURNE/compare?with_suburb=SHEPPARTON")
if [[ "$code" == "200" ]]; then
  if jq -e 'has("CRANBOURNE") and has("SHEPPARTON")' /tmp/apitest_body.json >/dev/null; then
    pass "compare CRANBOURNE vs SHEPPARTON"
  else
    fail "compare keys missing"
  fi
else
  fail "compare HTTP $code"
fi

code=$(http_code "$BASE/suburbs/CRANBOURNE/similar?limit=3")
[[ "$code" == "200" ]] && [[ "$(jq 'length' /tmp/apitest_body.json)" -le 3 ]] && pass "similar suburbs" || fail "similar $code"

section "Validation (limit bounds)"
code=$(http_code "$BASE/suburbs/?limit=250")
[[ "$code" == "422" ]] && pass "limit>200 -> 422" || fail "expected 422 for limit=250 got $code"

section "CORS (browser contract)"
# Production app + arbitrary Lovable preview should both get ACAO after recent deploy
for origin in "https://aussiepropertydata.lovable.app" "https://branch-preview-123.lovable.app" "https://9d387518-e185-4a1e-aecf-4e7c4d6e163b.lovableproject.com"; do
  h=$(curl -sS -I -H "Origin: $origin" "$BASE/suburbs/?limit=1" | tr -d '\r' | grep -i "^access-control-allow-origin:" || true)
  if echo "$h" | grep -q "access-control-allow-origin"; then
    pass "CORS GET Origin $origin"
  else
    fail "missing ACAO for Origin $origin"
  fi
done
code=$(curl -sS -o /dev/null -w "%{http_code}" -X OPTIONS "$BASE/suburbs/filter" \
  -H "Origin: https://preview-test.lovable.app" \
  -H "Access-Control-Request-Method: POST")
if [[ "$code" == "200" ]]; then
  pass "CORS OPTIONS preflight Lovable preview"
else
  fail "OPTIONS preflight got $code (expected 200 for *.lovable.app)"
fi

section "Concurrent /health (25 parallel)"
ok=0
tmp=$(mktemp)
for i in $(seq 1 25); do
  curl -sS -o /dev/null -w "%{http_code}\n" "$BASE/health" >>"$tmp" &
done
wait
ok=$(grep -c '^200$' "$tmp" || true)
rm -f "$tmp"
if [[ "$ok" -eq 25 ]]; then
  pass "25 concurrent health checks all 200"
else
  fail "concurrent health: $ok/25 returned 200"
fi

section "Docs (production may disable)"
code=$(http_code "$BASE/docs")
if [[ "$code" == "200" ]] || [[ "$code" == "404" ]]; then
  pass "/docs returns $code (expected 404 when docs disabled in prod)"
else
  fail "/docs unexpected $code"
fi

code=$(http_code "$BASE/openapi.json")
[[ "$code" == "200" ]] && jq -e '.openapi != null' /tmp/apitest_body.json >/dev/null && pass "openapi.json" || fail "openapi.json $code"

section "Calculators"
code=$(http_code "$BASE/calculators/stamp-duty?price=680000&first_home_buyer=false")
if [[ "$code" == "200" ]] && jq -e '.stamp_duty > 0 and .purchase_price == 680000 and (.stamp_duty_formatted | startswith("$"))' /tmp/apitest_body.json >/dev/null; then
  pass "GET /calculators/stamp-duty"
else
  fail "stamp-duty $code $(head -c 200 /tmp/apitest_body.json)"
fi
code=$(http_code "$BASE/calculators/yield?purchase_price=680000&weekly_rent=550")
if [[ "$code" == "200" ]] && jq -e '.gross_yield_pct > 0 and (.verdict | length) > 20' /tmp/apitest_body.json >/dev/null; then
  pass "GET /calculators/yield"
else
  fail "yield calculator $code $(head -c 200 /tmp/apitest_body.json)"
fi

section "CSV export"
csv_head=$(curl -sS "$BASE/suburbs/export?limit=3" | head -1)
if echo "$csv_head" | grep -q "suburb,postcode,is_metro"; then
  pass "GET /suburbs/export CSV header"
else
  fail "export CSV bad header: $csv_head"
fi

section "Market: benchmarks align with headline averages"
code=$(http_code "$BASE/market/summary")
if [[ "$code" == "200" ]] && jq -e '
  (.benchmarks.vic_avg_yield != null) and (.avg_yield != null)
  and ((.benchmarks.vic_avg_yield - .avg_yield | if . < 0 then -. else . end) < 0.02)
  and ((.benchmarks.vic_avg_growth_10yr - .avg_growth_10yr | if . < 0 then -. else . end) < 0.02)
  and ((.benchmarks.vic_avg_price_2023 - .avg_price | if . < 0 then -. else . end) < 1)
' /tmp/apitest_body.json >/dev/null; then
  pass "benchmarks mirror avg_yield / avg_growth / avg_price"
else
  fail "benchmark mismatch with headline stats"
fi

section "Pagination, sort, case"
code=$(http_code "$BASE/suburbs/?limit=2&offset=5&sort_by=price_2023&sort_dir=asc")
if [[ "$code" == "200" ]] && [[ "$(jq 'length' /tmp/apitest_body.json)" -eq 2 ]]; then
  pass "GET /suburbs offset + sort asc"
else
  fail "pagination/sort $code"
fi
code=$(http_code "$BASE/suburbs/cranbourne")
if [[ "$code" == "200" ]] && jq -e '.suburb == "CRANBOURNE"' /tmp/apitest_body.json >/dev/null; then
  pass "GET /suburbs/cranbourne (case-insensitive)"
else
  fail "lowercase suburb slug $code"
fi

section "Calculator edge cases"
code=$(http_code "$BASE/calculators/stamp-duty?price=580000&first_home_buyer=true")
if [[ "$code" == "200" ]] && jq -e '.stamp_duty == 0 and .first_home_buyer == true' /tmp/apitest_body.json >/dev/null; then
  pass "FHB stamp duty exemption <= 600k"
else
  fail "FHB stamp $code"
fi
code=$(http_code "$BASE/calculators/yield?purchase_price=500000&weekly_rent=0")
if [[ "$code" == "200" ]] && jq -e '.annual_rent == 0 and .gross_yield_pct == 0' /tmp/apitest_body.json >/dev/null; then
  pass "yield calculator zero rent"
else
  fail "yield zero rent $code"
fi

section "POST /suburbs/filter validation"
code=$(curl -sS -o /tmp/apitest_body.json -w "%{http_code}" -X POST "$BASE/suburbs/filter" \
  -H "Content-Type: application/json" -d '{"limit": 800}')
if [[ "$code" == "422" ]]; then
  pass "filter limit > 747 -> 422"
else
  fail "expected 422 for limit=800 got $code"
fi
code=$(curl -sS -o /tmp/apitest_body.json -w "%{http_code}" -X POST "$BASE/suburbs/filter" \
  -H "Content-Type: application/json" -d '{"min_price": 999999999, "limit": 10}')
if [[ "$code" == "200" ]] && [[ "$(jq 'length' /tmp/apitest_body.json)" -eq 0 ]]; then
  pass "filter empty result set"
else
  fail "empty filter expected 200 [] got $code"
fi

section "Search (no matches OK)"
code=$(http_code "$BASE/suburbs/search?q=zzzzzzzz&limit=5")
if [[ "$code" == "200" ]] && jq -e 'type == "array"' /tmp/apitest_body.json >/dev/null; then
  pass "/suburbs/search returns array (possibly empty)"
else
  fail "search zzzzz $code"
fi

section "Similar + compare edge"
code=$(http_code "$BASE/suburbs/cranbourne/similar?limit=2")
if [[ "$code" == "200" ]] && jq -e 'type == "array"' /tmp/apitest_body.json >/dev/null; then
  pass "/similar lowercase base suburb"
else
  fail "similar $code"
fi

echo ""
echo "=============================="
echo "RESULT: $PASS passed, $FAIL failed"
echo "=============================="
[[ "$FAIL" -eq 0 ]]
