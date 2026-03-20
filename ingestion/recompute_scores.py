"""
Recompute investment score and profile for all suburbs.
Run after any data update that changes signals used in the score.
"""
import asyncio
import asyncpg
import os

from api.scoring import compute_inv_profile, compute_inv_score, score_label_from_inv_score


async def recompute():
    conn = await asyncpg.connect(
        os.environ["SUPABASE_DB_URL"],
        statement_cache_size=0,
    )

    rows = await conn.fetch("""
        SELECT suburb, gross_yield, growth_10yr, pct_young_families,
               dist_to_station_km, irsd_decile, pop_growth_to_2036_pct,
               price_2023
        FROM suburbs
    """)

    scored = 0
    profiled = 0

    for row in rows:
        r = dict(row)
        score = compute_inv_score(r)
        profile = compute_inv_profile(r)
        label = score_label_from_inv_score(score)

        await conn.execute(
            """
            UPDATE suburbs
            SET inv_score = $2, inv_profile = $3, score_label = $4, data_updated_at = NOW()
            WHERE suburb = $1
        """,
            r["suburb"],
            score,
            profile,
            label,
        )

        if score:
            scored += 1
        profiled += 1

    await conn.close()
    print(f"Scores computed for {scored}/{profiled} suburbs")
    print(f"Profiles assigned for {profiled} suburbs")


if __name__ == "__main__":
    from ingestion.project_env import load_project_dotenv

    load_project_dotenv()
    asyncio.run(recompute())
