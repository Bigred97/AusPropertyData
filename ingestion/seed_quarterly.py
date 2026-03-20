"""Load Q2 2025 quarterly prices and sales volume."""
import json
import asyncio
import asyncpg
import os

# VPSR locality names often differ from canonical suburbs.suburb
_DIRECTIONAL_SUFFIXES = (
    " NORTH",
    " SOUTH",
    " EAST",
    " WEST",
    " UPPER",
    " LOWER",
)


def resolve_quarterly_name_to_canonical(
    raw_name: str, canonical: set[str]
) -> tuple[str | None, str]:
    """
    Map a quarterly JSON key to suburbs.suburb.
    Returns (canonical_name_or_none, match_kind).
    match_kind: 'direct' | 'directional' | 'parenthetical' | 'unmatched'
    """
    u = (raw_name or "").strip().upper()
    if not u:
        return None, "unmatched"
    if u in canonical:
        return u, "direct"
    for suf in _DIRECTIONAL_SUFFIXES:
        if u.endswith(suf):
            stripped = u[: -len(suf)].strip()
            if stripped in canonical:
                return stripped, "directional"
    if "(" in u:
        base = u.split("(", 1)[0].strip()
        if base in canonical:
            return base, "parenthetical"
    return None, "unmatched"


async def seed():
    conn = await asyncpg.connect(
        os.environ["SUPABASE_DB_URL"],
        statement_cache_size=0,
    )
    path = os.environ.get("QUARTERLY_PATH", "files/quarterly_q2_2025.json")
    if not os.path.exists(path):
        path = "quarterly_q2_2025.json"
    with open(path) as f:
        records = json.load(f)

    canonical_rows = await conn.fetch("SELECT suburb FROM suburbs")
    canonical = {row["suburb"] for row in canonical_rows}

    updated = 0
    updated_fallback = 0
    unmatched: list[str] = []

    for suburb, data in records.items():
        suburb_key = (suburb or "").strip().upper()
        if not suburb_key:
            continue
        price = data.get("price_q2_2025")
        sales = data.get("sales_q2_2025")
        if not price:
            continue

        resolved, kind = resolve_quarterly_name_to_canonical(suburb_key, canonical)
        if resolved is None:
            unmatched.append(suburb_key)
            continue

        result = await conn.execute(
            """
            UPDATE suburbs
            SET price_q2_2025 = $2,
                sales_volume_q2_2025 = $3,
                data_updated_at = NOW()
            WHERE suburb = $1
        """,
            resolved,
            int(price),
            int(sales) if sales is not None else None,
        )
        if result == "UPDATE 1":
            updated += 1
            if kind != "direct":
                updated_fallback += 1
        else:
            unmatched.append(f"{suburb_key} -> {resolved} (UPDATE 0)")

    await conn.close()

    z = len(unmatched)
    print(f"Updated: {updated} suburbs")
    print(f"Matched via fallback: {updated_fallback} suburbs")
    print(
        f"Still unmatched (skipped): {z} suburbs"
        + (f" — {unmatched}" if unmatched else "")
    )


if __name__ == "__main__":
    asyncio.run(seed())
