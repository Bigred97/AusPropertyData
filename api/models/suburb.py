from pydantic import BaseModel
from typing import Optional


class SuburbResponse(BaseModel):
    # Identity
    suburb: str
    postcode: str
    sa2_name: Optional[str] = None
    is_metro: bool

    # Price
    price_2023: Optional[int] = None
    price_2019: Optional[int] = None
    unit_price_2023: Optional[int] = None
    price_q2_2025: Optional[int] = None
    sales_volume_q2_2025: Optional[int] = None
    growth_10yr: Optional[float] = None
    growth_pa: Optional[float] = None

    # Yield
    rent_3br_wk: Optional[int] = None
    gross_yield: Optional[float] = None

    # Demographics
    population: Optional[int] = None
    pct_young_families: Optional[float] = None
    pct_seniors: Optional[float] = None
    pct_children: Optional[float] = None

    # SEIFA
    irsd_score: Optional[float] = None
    irsd_decile: Optional[int] = None
    irsad_score: Optional[float] = None
    ieo_score: Optional[float] = None

    # Transport
    dist_to_station_km: Optional[float] = None
    nearest_station: Optional[str] = None

    # VIF projections
    pop_growth_to_2036_pct: Optional[float] = None
    pop_2036_projected: Optional[int] = None
    dw_growth_pct: Optional[float] = None

    # Scores
    inv_score: Optional[float] = None
    inv_profile: Optional[str] = None
    score_label: Optional[str] = None
    summary: Optional[str] = None

    # vs Victorian averages (detail only)
    growth_vs_avg: Optional[str] = None
    yield_vs_avg: Optional[str] = None
    price_vs_avg: Optional[str] = None

    class Config:
        from_attributes = True


class SuburbListItem(BaseModel):
    suburb: str
    postcode: str
    is_metro: bool
    price_2023: Optional[int] = None
    growth_10yr: Optional[float] = None
    gross_yield: Optional[float] = None
    irsd_decile: Optional[int] = None
    pop_growth_to_2036_pct: Optional[float] = None
    inv_score: Optional[float] = None
    inv_profile: Optional[str] = None
    score_label: Optional[str] = None
    summary: Optional[str] = None
