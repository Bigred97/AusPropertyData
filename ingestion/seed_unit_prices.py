"""Load unit prices from unit_prices.json into suburbs table."""
import json
import asyncio
import asyncpg
import os


async def seed():
    conn = await asyncpg.connect(
        os.environ["SUPABASE_DB_URL"],
        statement_cache_size=0,
    )
    path = os.environ.get("UNIT_PRICES_PATH", "files/unit_prices.json")
    if not os.path.exists(path):
        path = "unit_prices.json"
    with open(path) as f:
        records = json.load(f)

    updated = 0
    for r in records:
        suburb = (r.get("suburb") or "").strip().upper()
        if not suburb:
            continue
        price = r.get("unit_price_2023")
        if price is None:
            continue
        result = await conn.execute(
            """
            UPDATE suburbs
            SET unit_price_2023 = $2, data_updated_at = NOW()
            WHERE suburb = $1
        """,
            suburb,
            int(price),
        )
        if result == "UPDATE 1":
            updated += 1

    await conn.close()
    print(f"Updated unit prices for {updated}/{len(records)} suburbs")


if __name__ == "__main__":
    asyncio.run(seed())
