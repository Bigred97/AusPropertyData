# AussiePropertyData API — Comprehensive Test Report

**Base URL:** https://auspropertydata-production.up.railway.app  
**Tested:** $(date)

---

## Endpoint Tests

| # | Endpoint | Status | Result |
|---|----------|--------|--------|
| 1 | `GET /health` | ✅ 200 | `{"status":"ok"}` |
| 2 | `GET /market/summary` | ✅ 200 | 747 suburbs, avg_quarterly_sales: 34 |
| 3 | `GET /suburbs/ABBOTSFORD` | ✅ 200 | unit_price_2023: 530000, price_q2_2025: 1295000 |
| 4 | `GET /suburbs/?limit=5` | ✅ 200 | Returns 5 rows, sorted by inv_score |
| 5 | `GET /suburbs/?is_metro=true&min_price=500000&max_price=800000` | ✅ 200 | Filters applied correctly |
| 6 | `GET /suburbs/top?profile=yield_hunter&limit=5` | ✅ 200 | Morwell #1 (6.22% yield) |
| 7 | `GET /suburbs/search?q=cran&limit=5` | ✅ 200 | Fuzzy search returns Cranbourne variants |
| 8 | `POST /suburbs/filter` | ✅ 200 | Complex filters work |
| 9 | `GET /suburbs/CRANBOURNE/history` | ✅ 200 | 11 years (2013–2023) |
| 10 | `GET /suburbs/MORWELL/compare?with_suburb=SHEPPARTON` | ✅ 200 | Side-by-side comparison |
| 11 | `GET /suburbs/CRANBOURNE/similar?limit=3` | ✅ 200 | Returns similar suburbs |
| 12 | `GET /suburbs/top?profile=*` | ✅ 200 | All 4 profiles work |
| 13 | `GET /docs` | ✅ 200 | Swagger UI |
| 14 | `GET /openapi.json` | ✅ 200 | OpenAPI spec |

---

## Edge Cases

| Test | Expected | Actual |
|------|----------|--------|
| Invalid suburb (404) | 404 | ✅ 404 |
| No history (404) | 404 | ✅ 404 |
| Search q too short (422) | 422 | ✅ 422 |
| Limit > 200 (422) | 422 | ✅ 422 |

---

## Load Test

| Test | Result |
|------|--------|
| 20 concurrent `/health` | All 200 |

---

## Data Integrity

| Field | ABBOTSFORD | CRANBOURNE |
|-------|------------|------------|
| unit_price_2023 | 530000 | — |
| price_q2_2025 | 1295000 | 713500 |
| sales_volume_q2_2025 | 21 | 103 |
| Price history | — | 11 years |

---

## Verdict

**All tests passed.** API is production-ready.
