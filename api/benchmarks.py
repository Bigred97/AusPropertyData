"""Victorian-wide benchmark aggregates for /market/summary and suburb detail."""

VIC_BENCHMARKS_SQL = """
SELECT
    ROUND(AVG(gross_yield)::numeric, 2) AS vic_avg_yield,
    ROUND(AVG(growth_10yr)::numeric, 1) AS vic_avg_growth_10yr,
    ROUND(AVG(price_2023)::numeric, 0) AS vic_avg_price_2023,
    ROUND(
        (PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY irsd_decile))::numeric,
        1
    ) AS vic_median_irsd_decile,
    ROUND(
        (
            100.0
            * COUNT(*) FILTER (WHERE growth_10yr >= 100)::numeric
            / NULLIF(COUNT(*), 0)
        )::numeric,
        1
    ) AS vic_pct_suburbs_doubled
FROM suburbs
"""

BENCH_KEYS = (
    "vic_avg_yield",
    "vic_avg_growth_10yr",
    "vic_avg_price_2023",
    "vic_median_irsd_decile",
    "vic_pct_suburbs_doubled",
)

# One round-trip: suburb row + benchmarks (s.* includes all stored columns).
SUBURB_DETAIL_WITH_BENCHMARKS_SQL = f"""
SELECT s.*,
    b.vic_avg_yield,
    b.vic_avg_growth_10yr,
    b.vic_avg_price_2023,
    b.vic_median_irsd_decile,
    b.vic_pct_suburbs_doubled
FROM suburbs s
CROSS JOIN ({VIC_BENCHMARKS_SQL.strip()}) AS b
WHERE s.suburb = $1
"""


async def fetch_vic_benchmarks(conn) -> dict:
    row = await conn.fetchrow(VIC_BENCHMARKS_SQL)
    return dict(row) if row else {}
