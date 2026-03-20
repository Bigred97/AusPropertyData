import csv
import io
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.benchmarks import BENCH_KEYS, SUBURB_DETAIL_WITH_BENCHMARKS_SQL
from api.column_probe import export_columns, list_select_columns
from api.db import get_conn
from api.models.filters import SuburbFilterRequest
from api.models.suburb import SuburbListItem, SuburbResponse
from api.scoring import score_label_from_inv_score, vs_average
from api.suburb_filters import build_suburb_filter_where

router = APIRouter()

ALLOWED_SORT = {
    "inv_score",
    "price_2023",
    "growth_10yr",
    "gross_yield",
    "pop_growth_to_2036_pct",
}


def _sort_clause(sort_by: str, sort_dir: str) -> tuple[str, str]:
    sb = sort_by if sort_by in ALLOWED_SORT else "inv_score"
    direction = "DESC" if sort_dir == "desc" else "ASC"
    return sb, direction


def _enrich_list_row(d: dict) -> dict:
    """Ensure score_label/summary always present for list responses (Pydantic + frontend)."""
    if d.get("score_label") is None and d.get("inv_score") is not None:
        d["score_label"] = score_label_from_inv_score(d["inv_score"])
    if "summary" not in d:
        d["summary"] = None
    return d


def _enrich_list_rows(rows) -> list[dict]:
    return [_enrich_list_row(dict(r)) for r in rows]


@router.get("/", response_model=list[SuburbListItem])
async def list_suburbs(
    is_metro: Optional[bool] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = "inv_score",
    sort_dir: str = "desc",
    conn=Depends(get_conn),
):
    """List suburbs with optional filters. Used for browse/search pages."""
    sb, direction = _sort_clause(sort_by, sort_dir)
    sel = list_select_columns()

    conditions = ["1=1"]
    params = []
    p = 1

    if is_metro is not None:
        conditions.append(f"is_metro = ${p}")
        params.append(is_metro)
        p += 1
    if min_price is not None:
        conditions.append(f"price_2023 >= ${p}")
        params.append(min_price)
        p += 1
    if max_price is not None:
        conditions.append(f"price_2023 <= ${p}")
        params.append(max_price)
        p += 1

    where = " AND ".join(conditions)
    params.extend([limit, offset])
    query = f"""
        SELECT {sel}
        FROM suburbs
        WHERE {where}
        ORDER BY {sb} {direction} NULLS LAST
        LIMIT ${p} OFFSET ${p + 1}
    """
    rows = await conn.fetch(query, *params)
    return _enrich_list_rows(rows)


@router.get("/top", response_model=list[SuburbListItem])
async def top_suburbs(
    profile: str = Query(
        "balanced",
        description="yield_hunter | growth_chaser | gentrification | balanced",
    ),
    limit: int = Query(10, ge=1, le=50),
    conn=Depends(get_conn),
):
    """Pre-built ranked lists for homepage tables."""
    sort_map = {
        "yield_hunter": "gross_yield",
        "growth_chaser": "pop_growth_to_2036_pct",
        "gentrification": "pct_young_families",
        "balanced": "inv_score",
    }
    sort_col = sort_map.get(profile, "inv_score")
    sel = list_select_columns()
    rows = await conn.fetch(
        f"""
        SELECT {sel}
        FROM suburbs
        WHERE {sort_col} IS NOT NULL
        ORDER BY {sort_col} DESC NULLS LAST
        LIMIT $1
    """,
        limit,
    )
    return _enrich_list_rows(rows)


@router.get("/search", response_model=list[SuburbListItem])
async def search_suburbs(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    conn=Depends(get_conn),
):
    """Fuzzy suburb name search. Powers the search bar."""
    sel = list_select_columns()
    rows = await conn.fetch(
        f"""
        SELECT {sel}
        FROM suburbs
        WHERE suburb % $1 OR suburb ILIKE $2
        ORDER BY similarity(suburb, $1) DESC
        LIMIT $3
    """,
        q.upper(),
        f"%{q.upper()}%",
        limit,
    )
    return _enrich_list_rows(rows)


@router.post("/filter", response_model=list[SuburbListItem])
async def filter_suburbs(
    filters: SuburbFilterRequest,
    conn=Depends(get_conn),
):
    """Full investor screener. POST any combination of filters, get ranked results."""
    where, params, p = build_suburb_filter_where(filters)
    sb, direction = _sort_clause(
        filters.sort_by or "inv_score",
        filters.sort_dir or "desc",
    )
    params.extend([filters.limit, filters.offset])
    sel = list_select_columns()
    rows = await conn.fetch(
        f"""
        SELECT {sel}
        FROM suburbs
        WHERE {where}
        ORDER BY {sb} {direction} NULLS LAST
        LIMIT ${p} OFFSET ${p + 1}
    """,
        *params,
    )
    return _enrich_list_rows(rows)


_PROFILE_VALUES = frozenset(
    {
        "yield_hunter",
        "growth_chaser",
        "gentrification",
        "balanced",
        "general",
    }
)


@router.get("/export")
async def export_suburbs_csv(
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_yield: Optional[float] = None,
    min_growth: Optional[float] = Query(None, description="min_growth_10yr"),
    is_metro: Optional[bool] = None,
    min_seifa: Optional[int] = Query(None, description="min irsd_decile"),
    max_seifa: Optional[int] = Query(None, description="max irsd_decile"),
    max_train_distance: Optional[float] = Query(
        None, description="max_dist_to_station_km"
    ),
    min_pop_growth: Optional[float] = Query(None, description="min pop growth 2036 %"),
    profile: Optional[str] = None,
    postcode_prefix: Optional[str] = None,
    min_pct_young_families: Optional[float] = None,
    limit: int = Query(500, ge=1, le=747),
    sort_by: str = "inv_score",
    sort_dir: Literal["asc", "desc"] = "desc",
    conn=Depends(get_conn),
):
    """Download screener results as CSV (same filters as POST /filter)."""
    inv_profile = profile if profile in _PROFILE_VALUES else None
    filters = SuburbFilterRequest(
        min_price=min_price,
        max_price=max_price,
        min_yield=min_yield,
        min_growth_10yr=min_growth,
        min_seifa_decile=min_seifa,
        max_seifa_decile=max_seifa,
        max_dist_to_station_km=max_train_distance,
        min_pop_growth_2036=min_pop_growth,
        is_metro=is_metro,
        inv_profile=inv_profile,
        postcode_prefix=postcode_prefix,
        min_pct_young_families=min_pct_young_families,
        limit=limit,
        offset=0,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    where, params, p = build_suburb_filter_where(filters)
    sb, direction = _sort_clause(filters.sort_by or "inv_score", filters.sort_dir or "desc")
    params.extend([filters.limit, filters.offset])
    cols = export_columns()
    export_sql = ", ".join(cols)
    rows = await conn.fetch(
        f"""
        SELECT {export_sql}
        FROM suburbs
        WHERE {where}
        ORDER BY {sb} {direction} NULLS LAST
        LIMIT ${p} OFFSET ${p + 1}
    """,
        *params,
    )

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()

    def cell(v):
        if v is None:
            return ""
        if isinstance(v, Decimal):
            f = float(v)
            return int(f) if f == int(f) else f
        return v

    for r in rows:
        d = dict(r)
        writer.writerow({k: cell(d.get(k)) for k in cols})

    data = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="aussiepropertydata-export.csv"'
        },
    )


@router.get("/{suburb_name}", response_model=SuburbResponse)
async def get_suburb(suburb_name: str, conn=Depends(get_conn)):
    """Full suburb profile — all fields. Powers suburb detail pages."""
    row = await conn.fetchrow(
        SUBURB_DETAIL_WITH_BENCHMARKS_SQL,
        suburb_name.strip().upper(),
    )
    if not row:
        raise HTTPException(404, detail=f"Suburb '{suburb_name}' not found")

    d = dict(row)
    bench = {k: d.pop(k) for k in BENCH_KEYS}

    gy = bench.get("vic_avg_yield")
    gr = bench.get("vic_avg_growth_10yr")
    pr = bench.get("vic_avg_price_2023")

    d["growth_vs_avg"] = (
        vs_average(d.get("growth_10yr"), float(gr), "10yr growth")
        if gr is not None
        else None
    )
    d["yield_vs_avg"] = (
        vs_average(d.get("gross_yield"), float(gy), "yield") if gy is not None else None
    )
    d["price_vs_avg"] = (
        vs_average(d.get("price_2023"), float(pr), "price", higher_is_better=False)
        if pr is not None
        else None
    )
    if d.get("score_label") is None and d.get("inv_score") is not None:
        d["score_label"] = score_label_from_inv_score(d["inv_score"])
    if "summary" not in d:
        d["summary"] = None
    return d


@router.get("/{suburb_name}/history")
async def suburb_history(suburb_name: str, conn=Depends(get_conn)):
    """11-year annual price series. Powers the price chart."""
    rows = await conn.fetch(
        """
        SELECT year, median_price, num_sales, property_type
        FROM suburb_price_history
        WHERE suburb = $1
        ORDER BY year ASC, property_type ASC
    """,
        suburb_name.strip().upper(),
    )
    if not rows:
        raise HTTPException(404, detail="No history found")
    return [dict(r) for r in rows]


@router.get("/{suburb_name}/compare")
async def compare_suburbs(
    suburb_name: str,
    with_suburb: str = Query(...),
    conn=Depends(get_conn),
):
    """Side-by-side comparison of two suburbs. All fields."""
    suburbs = await conn.fetch(
        "SELECT * FROM suburbs WHERE suburb = ANY($1)",
        [suburb_name.strip().upper(), with_suburb.strip().upper()],
    )
    if len(suburbs) < 2:
        raise HTTPException(404, detail="One or both suburbs not found")
    return {s["suburb"]: dict(s) for s in suburbs}


@router.get("/{suburb_name}/similar", response_model=list[SuburbListItem])
async def similar_suburbs(
    suburb_name: str,
    limit: int = Query(5, ge=1, le=10),
    conn=Depends(get_conn),
):
    """Suburbs with similar investment profile score."""
    base = await conn.fetchrow(
        "SELECT inv_score, price_2023, is_metro FROM suburbs WHERE suburb = $1",
        suburb_name.strip().upper(),
    )
    if not base:
        raise HTTPException(404, detail="Suburb not found")
    sel = list_select_columns()
    rows = await conn.fetch(
        f"""
        SELECT {sel}
        FROM suburbs
        WHERE suburb != $1
          AND is_metro = $2
          AND ABS(COALESCE(inv_score,0) - $3) < 15
          AND ABS(COALESCE(price_2023,0) - $4) < 200000
        ORDER BY ABS(COALESCE(inv_score,0) - $3) ASC
        LIMIT $5
    """,
        suburb_name.strip().upper(),
        base["is_metro"],
        float(base["inv_score"] or 0),
        int(base["price_2023"] or 0),
        limit,
    )
    return _enrich_list_rows(rows)
