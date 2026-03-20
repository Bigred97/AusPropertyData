"""Victorian stamp duty and rental yield calculators (indicative)."""

from fastapi import APIRouter, Query

from api.models.calculators import StampDutyResponse, YieldCalculatorResponse

router = APIRouter()

VIC_AVG_YIELD = 3.3


def _money(n: int) -> str:
    return f"${n:,}"


def _compute_base_stamp_duty(price: int) -> float:
    if price <= 0:
        return 0.0
    if price <= 25_000:
        return price * 0.014
    if price <= 130_000:
        return 350 + (price - 25_000) * 0.024
    if price <= 960_000:
        return 2_870 + (price - 130_000) * 0.06
    return price * 0.055


def _apply_fhb(price: int, duty: float) -> float:
    if price <= 600_000:
        return 0.0
    if price <= 750_000:
        return duty * (1 - (750_000 - price) / 150_000)
    return duty


@router.get("/stamp-duty", response_model=StampDutyResponse)
async def stamp_duty_calculator(
    price: int = Query(..., ge=1, description="Purchase price"),
    first_home_buyer: bool = Query(False),
):
    base = _compute_base_stamp_duty(price)
    final = _apply_fhb(price, base) if first_home_buyer else base
    stamp = int(round(final))
    conveyancing = 1800
    total = stamp + conveyancing
    note = (
        "Conveyancing estimate is approximate. "
        "Stamp duty is indicative only — confirm with your solicitor."
    )
    return StampDutyResponse(
        purchase_price=price,
        first_home_buyer=first_home_buyer,
        stamp_duty=stamp,
        stamp_duty_formatted=_money(stamp),
        conveyancing_estimate=conveyancing,
        total_upfront_cost=total,
        total_upfront_formatted=_money(total),
        note=note,
    )


@router.get("/yield", response_model=YieldCalculatorResponse)
async def yield_calculator(
    purchase_price: int = Query(..., ge=1),
    weekly_rent: int = Query(..., ge=0),
):
    annual_rent = weekly_rent * 52
    gross_pct = round((annual_rent / purchase_price) * 100, 2)
    gross_fmt = f"{gross_pct:.1f}%"
    monthly_income = round(annual_rent / 12)
    annual_expenses = round(annual_rent * 0.22)
    net_pct = round(((annual_rent - annual_expenses) / purchase_price) * 100, 2)
    net_note = (
        "Net yield estimate deducts ~22% for rates, insurance, management fees "
        "and maintenance. Actual costs vary."
    )
    if gross_pct >= VIC_AVG_YIELD:
        vs_vic = f"Above Victorian average of {VIC_AVG_YIELD}%"
    else:
        vs_vic = f"Below Victorian average of {VIC_AVG_YIELD}%"

    if gross_pct >= 5.0:
        verdict = (
            "Strong yield. This suburb is in the top tier for Victorian rental returns."
        )
    elif gross_pct >= 4.0:
        verdict = (
            "Solid yield. Above the Victorian average of 3.3% and positive cash flow "
            "is achievable depending on your loan structure."
        )
    elif gross_pct >= 3.0:
        verdict = (
            "Moderate yield. Below the Victorian average. This is a growth play — "
            "capital appreciation will drive returns more than rental income."
        )
    else:
        verdict = (
            "Low yield. Suits investors prioritising capital growth over cash flow."
        )

    return YieldCalculatorResponse(
        purchase_price=purchase_price,
        weekly_rent=weekly_rent,
        annual_rent=annual_rent,
        gross_yield_pct=gross_pct,
        gross_yield_formatted=gross_fmt,
        monthly_income_estimate=monthly_income,
        annual_expenses_estimate=annual_expenses,
        net_yield_estimate_pct=net_pct,
        net_yield_note=net_note,
        vs_vic_average=vs_vic,
        verdict=verdict,
    )
