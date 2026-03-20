"""
Detect optional UX columns on `suburbs` so the API works before and after migration 002.
"""

from __future__ import annotations

_has_summary: bool = False
_has_score_label: bool = False


async def load_column_flags(conn) -> None:
    global _has_summary, _has_score_label
    rows = await conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'suburbs'
          AND column_name IN ('summary', 'score_label')
        """
    )
    found = {r["column_name"] for r in rows}
    _has_summary = "summary" in found
    _has_score_label = "score_label" in found


def has_summary_column() -> bool:
    return _has_summary


def has_score_label_column() -> bool:
    return _has_score_label


def list_select_columns() -> str:
    """Comma-separated SELECT list for list-style suburb endpoints (no trailing comma)."""
    base = """
    suburb, postcode, is_metro, price_2023, growth_10yr,
    gross_yield, irsd_decile, pop_growth_to_2036_pct,
    inv_score, inv_profile""".strip()
    extra = []
    if _has_score_label:
        extra.append("score_label")
    if _has_summary:
        extra.append("summary")
    if not extra:
        return base
    return base + ", " + ", ".join(extra)


def export_columns() -> list[str]:
    cols = [
        "suburb",
        "postcode",
        "is_metro",
        "price_2023",
        "unit_price_2023",
        "price_q2_2025",
        "gross_yield",
        "growth_10yr",
        "growth_pa",
        "irsd_decile",
        "pct_young_families",
        "pct_seniors",
        "population",
        "dist_to_station_km",
        "nearest_station",
        "pop_growth_to_2036_pct",
        "sales_volume_q2_2025",
        "inv_score",
        "inv_profile",
    ]
    if _has_score_label:
        cols.append("score_label")
    if _has_summary:
        cols.append("summary")
    return cols
