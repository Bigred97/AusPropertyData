"""
Generate plain-English summary for every suburb row.
Run after migration 002. Requires SUPABASE_DB_URL.
"""
import asyncio
import asyncpg
import os

from api.scoring import generate_suburb_summary


async def run():
    conn = await asyncpg.connect(
        os.environ["SUPABASE_DB_URL"],
        statement_cache_size=0,
    )
    rows = await conn.fetch("SELECT * FROM suburbs")
    for row in rows:
        summary = generate_suburb_summary(dict(row))
        await conn.execute(
            "UPDATE suburbs SET summary = $1 WHERE suburb = $2",
            summary,
            row["suburb"],
        )
    await conn.close()
    print(f"Done: {len(rows)} summaries generated")


if __name__ == "__main__":
    asyncio.run(run())
