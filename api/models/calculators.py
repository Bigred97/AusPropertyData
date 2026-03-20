from pydantic import BaseModel


class StampDutyResponse(BaseModel):
    purchase_price: int
    first_home_buyer: bool
    stamp_duty: int
    stamp_duty_formatted: str
    conveyancing_estimate: int
    total_upfront_cost: int
    total_upfront_formatted: str
    note: str


class YieldCalculatorResponse(BaseModel):
    purchase_price: int
    weekly_rent: int
    annual_rent: int
    gross_yield_pct: float
    gross_yield_formatted: str
    monthly_income_estimate: int
    annual_expenses_estimate: int
    net_yield_estimate_pct: float
    net_yield_note: str
    vs_vic_average: str
    verdict: str
