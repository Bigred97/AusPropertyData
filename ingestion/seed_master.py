"""
One-time seed: loads master_dataset.json into the suburbs table.
Run once after schema is created.
Usage: python -m ingestion.seed_master
"""
import json
import asyncio
import os
from datetime import datetime

from api.scoring import compute_inv_profile
from ingestion.utils import asyncpg_connect_supabase


def _num(v):
    """Coerce value to number or None. Handles 'NA', '', null."""
    if v is None or v == "" or (isinstance(v, str) and v.upper() == "NA"):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v) if "." in str(v) else int(v)
    except (ValueError, TypeError):
        return None


async def seed():
    dataset_path = os.environ.get("MASTER_DATASET_PATH", "master_dataset.json")
    with open(dataset_path) as f:
        suburbs = json.load(f)

    conn = await asyncpg_connect_supabase(statement_cache_size=0)

    upserted = 0
    for r in suburbs:
        inv_profile = compute_inv_profile(r)
        try:
            suburb_key = (r.get("suburb") or "").strip().upper()
            if not suburb_key:
                continue
            await conn.execute(
                """
                INSERT INTO suburbs (
                    suburb, postcode, sa2_name, is_metro,
                    price_2019, price_2023, growth_10yr, growth_pa,
                    rent_3br_wk, gross_yield,
                    population, pct_young_families, pct_seniors, pct_children,
                    irsd_score, irsd_decile, irsad_score, irsad_decile,
                    ieo_score, ieo_decile,
                    dist_to_station_km, nearest_station,
                    pop_growth_to_2031_pct, pop_growth_to_2036_pct,
                    pop_2021_vif, pop_2036_projected,
                    dw_growth_pct, projected_yf_pct_2036,
                    inv_score, inv_profile, data_updated_at
                ) VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,
                    $15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,
                    $27,$28,$29,$30,$31
                )
                ON CONFLICT (suburb) DO UPDATE SET
                    price_2023 = EXCLUDED.price_2023,
                    growth_10yr = EXCLUDED.growth_10yr,
                    gross_yield = EXCLUDED.gross_yield,
                    irsd_decile = EXCLUDED.irsd_decile,
                    pop_growth_to_2036_pct = EXCLUDED.pop_growth_to_2036_pct,
                    inv_score = EXCLUDED.inv_score,
                    inv_profile = EXCLUDED.inv_profile,
                    data_updated_at = NOW()
            """,
                suburb_key,
                r.get("postcode"),
                r.get("sa2_name"),
                r.get("is_metro", False),
                _num(r.get("price_2019")),
                _num(r.get("price_2023")),
                _num(r.get("growth_10yr")),
                _num(r.get("growth_pa")),
                _num(r.get("rent_3br_wk")),
                _num(r.get("gross_yield")),
                _num(r.get("population")),
                _num(r.get("pct_young_families")),
                _num(r.get("pct_seniors")),
                _num(r.get("pct_children")),
                _num(r.get("irsd_score")),
                _num(r.get("irsd_decile")),
                _num(r.get("irsad_score")),
                _num(r.get("irsad_decile")),
                _num(r.get("ieo_score")),
                _num(r.get("ieo_decile")),
                _num(r.get("dist_to_station_km")),
                r.get("nearest_station"),
                _num(r.get("pop_growth_to_2031_pct")),
                _num(r.get("pop_growth_to_2036_pct")),
                _num(r.get("pop_2021_vif")),
                _num(r.get("pop_2036_projected")),
                _num(r.get("dw_growth_pct")),
                _num(r.get("projected_yf_pct_2036")),
                _num(r.get("final_score_v2") or r.get("final_score")),
                inv_profile,
                datetime.utcnow(),
            )
            upserted += 1
        except Exception as e:
            print(f"  ERROR on {suburb_key}: {e}")

    await conn.close()
    print(f"Seeded {upserted}/{len(suburbs)} suburbs.")


if __name__ == "__main__":
    asyncio.run(seed())
