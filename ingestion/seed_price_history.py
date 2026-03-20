# ingestion/seed_price_history.py

import json
import asyncio
import asyncpg
import os

YEAR_FIELDS = {
    2013: "price_2013",
    2014: "price_2014",
    2015: "price_2015",
    2016: "price_2016",
    2017: "price_2017",
    2018: "price_2018",
    2019: "price_2019",
    2020: "price_2020",
    2021: "price_2021",
    2022: "price_2022",
    2023: "price_2023",
}


async def seed():
    conn = await asyncpg.connect(
        os.environ["SUPABASE_DB_URL"],
        statement_cache_size=0,
    )
    with open("master_dataset.json") as f:
        suburbs = json.load(f)

    # Clear existing 2-point history first
    await conn.execute(
        "DELETE FROM suburb_price_history WHERE property_type = 'house'"
    )

    rows = []
    for r in suburbs:
        suburb = (r.get("suburb") or "").strip().upper()
        if not suburb:
            continue
        for year, field in YEAR_FIELDS.items():
            price = r.get(field)
            if price and isinstance(price, (int, float)) and price > 0:
                rows.append((suburb, year, int(price), "house"))

    await conn.executemany(
        """
        INSERT INTO suburb_price_history (suburb, year, median_price, property_type)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (suburb, year, property_type) DO NOTHING
    """,
        rows,
    )

    await conn.close()
    print(
        f"Inserted {len(rows)} price history records across {len(suburbs)} suburbs"
    )


if __name__ == "__main__":
    asyncio.run(seed())
