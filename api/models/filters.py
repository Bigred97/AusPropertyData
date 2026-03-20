from pydantic import BaseModel, Field
from typing import Optional, Literal


class SuburbFilterRequest(BaseModel):
    # Price filters
    min_price: Optional[int] = None
    max_price: Optional[int] = None

    # Yield filters
    min_yield: Optional[float] = None

    # Growth filters
    min_growth_10yr: Optional[float] = None

    # SEIFA filters
    min_seifa_decile: Optional[int] = None
    max_seifa_decile: Optional[int] = None

    # Demographics
    min_pct_young_families: Optional[float] = None

    # Transport
    max_dist_to_station_km: Optional[float] = None

    # Population growth
    min_pop_growth_2036: Optional[float] = None

    # Geography
    is_metro: Optional[bool] = None
    postcode_prefix: Optional[str] = None  # e.g. "30" matches all 30xx postcodes

    # Profile filter (matches DB inv_profile incl. legacy/general)
    inv_profile: Optional[
        Literal[
            "yield_hunter",
            "growth_chaser",
            "gentrification",
            "balanced",
            "general",
        ]
    ] = None

    # Sorting
    sort_by: Optional[str] = "inv_score"
    sort_dir: Optional[Literal["asc", "desc"]] = "desc"

    # Pagination
    limit: int = Field(default=50, ge=1, le=747)
    offset: int = Field(default=0, ge=0)
