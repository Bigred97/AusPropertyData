"""
Investment score and investor profile — single source of truth.
Used by API, seed_master, and recompute_scores.
"""

from __future__ import annotations

from typing import Any


def score_label_from_inv_score(inv_score: float | None) -> str | None:
    if inv_score is None:
        return None
    s = float(inv_score)
    if s >= 110:
        return "Strong opportunity"
    if s >= 90:
        return "Good opportunity"
    if s >= 70:
        return "Moderate"
    return "Limited upside"


def vs_average(
    value: float | int | None,
    benchmark: float,
    label: str,
    higher_is_better: bool = True,
) -> str | None:
    """Plain-English comparison vs a Victorian benchmark (5% band = in line)."""
    if value is None or benchmark == 0:
        return None
    v = float(value)
    diff = ((v - benchmark) / benchmark) * 100
    direction = "above" if diff > 0 else "below"
    if abs(diff) < 5:
        return f"In line with Victorian average {label}"
    return f"{abs(diff):.0f}% {direction} Victorian average {label}"


def generate_suburb_summary(r: dict[str, Any]) -> str:
    """
    2–4 sentence plain-English verdict from a suburbs row dict.
    Primary rule: first matching signal wins (priority order).
    """
    gy = r.get("gross_yield")
    gy_f = float(gy) if gy is not None else None
    growth = r.get("growth_10yr")
    growth_f = float(growth) if growth is not None else None
    pop = r.get("pop_growth_to_2036_pct")
    pop_f = float(pop) if pop is not None else None
    price = r.get("price_2023")
    price_i = int(price) if price is not None else None
    irsd = r.get("irsd_decile")
    irsd_i = int(irsd) if irsd is not None else None
    yf = r.get("pct_young_families")
    yf_f = float(yf) if yf is not None else None
    is_metro = bool(r.get("is_metro"))
    dist = r.get("dist_to_station_km")
    dist_f = float(dist) if dist is not None else None
    station = r.get("nearest_station")

    primary = "Established Victorian suburb with steady market fundamentals."

    if (
        gy_f is not None
        and growth_f is not None
        and gy_f >= 4.5
        and growth_f >= 80
    ):
        primary = "Strong cash flow suburb with solid historical growth."
    elif (
        pop_f is not None
        and price_i is not None
        and pop_f >= 150
        and price_i <= 700_000
    ):
        primary = "High future demand suburb at an accessible entry price."
    elif (
        irsd_i is not None
        and yf_f is not None
        and growth_f is not None
        and irsd_i <= 3
        and yf_f >= 33
        and growth_f >= 70
    ):
        primary = "Emerging suburb showing early gentrification signals."
    elif (
        is_metro
        and growth_f is not None
        and price_i is not None
        and growth_f >= 90
        and price_i <= 800_000
    ):
        primary = "Affordable metro suburb with above-average historical growth."
    elif gy_f is not None and pop_f is not None and gy_f >= 4.0 and pop_f >= 50:
        primary = "Balanced suburb offering both yield and future population demand."

    if gy_f is not None and gy_f >= 4.5:
        secondary = "Suits cash flow investors seeking income from day one."
    elif gy_f is not None and 3.0 <= gy_f < 4.5:
        secondary = "Moderate yield suits investors balancing growth and income."
    else:
        secondary = "Yield data limited — suits growth-focused investors with a longer horizon."

    parts = [primary, secondary]

    if pop_f is not None and pop_f >= 200:
        parts.append(
            "Government projections show exceptional population growth to 2036, signalling strong future housing demand."
        )
    elif pop_f is not None and 80 <= pop_f < 200:
        parts.append(
            "Solid population growth projected to 2036 supports long-term demand."
        )
    elif dist_f is not None and dist_f <= 2.0 and station:
        parts.append(
            f"Located {dist_f}km from {station}, providing strong transport access."
        )

    return " ".join(parts)


def compute_inv_score(r: dict) -> float | None:
    """
    Composite investment score — higher is better.
    Returns None if insufficient data.
    """
    if not r.get("gross_yield") or not r.get("growth_10yr"):
        return None

    yield_ = float(r.get("gross_yield") or 0)
    growth = float(r.get("growth_10yr") or 0)
    yf_pct = float(r.get("pct_young_families") or 20)
    dist = float(r.get("dist_to_station_km") or 10)
    irsd = int(r.get("irsd_decile") or 5)
    pop36 = min(float(r.get("pop_growth_to_2036_pct") or 0), 200)

    seifa_adj = (irsd - 5) * 1.5
    pop_signal = pop36 * 0.15

    return round(
        (yield_ * 15)
        + (growth * 0.3)
        + (yf_pct * 0.5)
        - (dist * 2)
        + seifa_adj
        + pop_signal,
        2,
    )


def compute_inv_profile(r: dict) -> str:
    """Classify suburb into investor profile based on signals."""
    yield_ = float(r.get("gross_yield") or 0)
    growth = float(r.get("growth_10yr") or 0)
    irsd = int(r.get("irsd_decile") or 5)
    yf = float(r.get("pct_young_families") or 0)
    pop36 = float(r.get("pop_growth_to_2036_pct") or 0)
    price = int(r.get("price_2023") or 999999)

    if yield_ >= 4.5:
        return "yield_hunter"
    elif pop36 >= 80 and price < 800000:
        return "growth_chaser"
    elif irsd <= 3 and yf >= 33 and growth >= 70:
        return "gentrification"
    elif yield_ >= 3.5 and growth >= 80 and pop36 >= 20:
        return "balanced"
    return "general"
