"""Shared WHERE clause for POST /suburbs/filter and GET /suburbs/export."""

from api.models.filters import SuburbFilterRequest


def build_suburb_filter_where(filters: SuburbFilterRequest) -> tuple[str, list, int]:
    """
    Returns (where_sql, param_list, next_param_index).
    Caller appends limit/offset using placeholders $next and $next+1.
    """
    conditions = ["1=1"]
    params: list = []
    p = 1

    def add(condition: str, value):
        nonlocal p
        conditions.append(condition.replace("?", f"${p}"))
        params.append(value)
        p += 1

    if filters.min_price is not None:
        add("price_2023 >= ?", filters.min_price)
    if filters.max_price is not None:
        add("price_2023 <= ?", filters.max_price)
    if filters.min_yield is not None:
        add("gross_yield >= ?", filters.min_yield)
    if filters.min_growth_10yr is not None:
        add("growth_10yr >= ?", filters.min_growth_10yr)
    if filters.min_seifa_decile is not None:
        add("irsd_decile >= ?", filters.min_seifa_decile)
    if filters.max_seifa_decile is not None:
        add("irsd_decile <= ?", filters.max_seifa_decile)
    if filters.min_pct_young_families is not None:
        add("pct_young_families >= ?", filters.min_pct_young_families)
    if filters.max_dist_to_station_km is not None:
        add("dist_to_station_km <= ?", filters.max_dist_to_station_km)
    if filters.min_pop_growth_2036 is not None:
        add("pop_growth_to_2036_pct >= ?", filters.min_pop_growth_2036)
    if filters.is_metro is not None:
        add("is_metro = ?", filters.is_metro)
    if filters.inv_profile is not None:
        add("inv_profile = ?", filters.inv_profile)
    if filters.postcode_prefix is not None:
        add("postcode LIKE ?", f"{filters.postcode_prefix}%")

    return " AND ".join(conditions), params, p
