from fastapi import APIRouter, Depends

from api.db import get_conn

router = APIRouter()


def _num(v):
    if v is None:
        return None
    return float(v)


# Single table scan: headline stats + benchmark block for nested JSON.
_MARKET_SUMMARY_SQL = """
SELECT
    COUNT(*)::bigint AS total_suburbs,
    ROUND(AVG(price_2023)::numeric, 0) AS avg_price,
    ROUND(AVG(CASE WHEN is_metro THEN price_2023 END)::numeric, 0) AS avg_metro_price,
    ROUND(AVG(CASE WHEN NOT is_metro THEN price_2023 END)::numeric, 0) AS avg_regional_price,
    ROUND(AVG(gross_yield)::numeric, 2) AS avg_yield,
    ROUND(AVG(CASE WHEN is_metro THEN gross_yield END)::numeric, 2) AS avg_metro_yield,
    ROUND(AVG(growth_10yr)::numeric, 1) AS avg_growth_10yr,
    COUNT(*) FILTER (WHERE growth_10yr >= 100)::bigint AS suburbs_doubled,
    COUNT(*) FILTER (WHERE gross_yield >= 4)::bigint AS suburbs_4pct_yield,
    ROUND(AVG(pop_growth_to_2036_pct)::numeric, 1) AS avg_pop_growth_2036,
    ROUND(AVG(sales_volume_q2_2025)::numeric, 0) AS avg_quarterly_sales,
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


@router.get("/summary")
async def market_summary(conn=Depends(get_conn)):
    """Victoria-wide market statistics (one DB round-trip)."""
    row = await conn.fetchrow(_MARKET_SUMMARY_SQL)
    if not row:
        return {"total_suburbs": 0, "benchmarks": {}}

    d = dict(row)
    median = d.pop("vic_median_irsd_decile", None)
    pct_doubled = d.pop("vic_pct_suburbs_doubled", None)

    d["benchmarks"] = {
        "vic_avg_yield": _num(d.get("avg_yield")),
        "vic_avg_growth_10yr": _num(d.get("avg_growth_10yr")),
        "vic_avg_price_2023": _num(d.get("avg_price")),
        "vic_median_irsd_decile": _num(median),
        "vic_pct_suburbs_doubled": _num(pct_doubled),
    }
    return d
