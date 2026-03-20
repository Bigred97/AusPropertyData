"""Load rent, yield, and unit prices from rent_yield_update.json into suburbs table."""
import json
import asyncio
import asyncpg
import os


async def seed():
    conn = await asyncpg.connect(
        os.environ["SUPABASE_DB_URL"],
        statement_cache_size=0,
    )
    path = os.environ.get("RENT_YIELD_PATH", "files/rent_yield_update.json")
    if not os.path.exists(path):
        path = "rent_yield_update.json"
    with open(path) as f:
        records = json.load(f)

    updated = 0
    for r in records:
        suburb = (r.get("suburb") or "").strip().upper()
        if not suburb:
            continue
        result = await conn.execute(
            """
            UPDATE suburbs
            SET rent_3br_wk = COALESCE($2, rent_3br_wk),
                rent_2br_wk = COALESCE($3, rent_2br_wk),
                unit_price_2023 = COALESCE($4, unit_price_2023),
                gross_yield = COALESCE($5, gross_yield),
                data_updated_at = NOW()
            WHERE suburb = $1
        """,
            suburb,
            r.get("rent_3br_wk"),
            r.get("rent_2br_wk"),
            r.get("unit_price_2023"),
            r.get("gross_yield"),
        )
        if result == "UPDATE 1":
            updated += 1

    await conn.close()
    print(f"Updated rent/yield for {updated}/{len(records)} suburbs")


if __name__ == "__main__":
    asyncio.run(seed())
