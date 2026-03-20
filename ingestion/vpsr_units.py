"""
VPSR quarterly unit (median) price ingestion.
Same XLS layout as houses; updates unit_price_2023 with the latest quarter median.

Source: https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-unit-by-suburb

Prefer VPSR_UNITS_XLS when land.vic blocks scripted downloads — see docs/DATA_SOURCES.md.
"""
import asyncio
import asyncpg
import os
from bs4 import BeautifulSoup

from ingestion.fetch import (
    first_ckan_go_to_resource,
    ingestion_http_client,
    land_vic_download_headers,
)
from ingestion.vpsr_parse import parse_vpsr_xls

CATALOGUE_URL = (
    "https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-unit-by-suburb"
)


def _require_db_url() -> str:
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("SUPABASE_DB_URL is required for VPSR unit DB ingestion")
    return url


async def get_latest_unit_download_url() -> tuple[str, str]:
    async with ingestion_http_client() as client:
        resp = await client.get(CATALOGUE_URL, timeout=30)
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    hit = first_ckan_go_to_resource(
        soup,
        CATALOGUE_URL,
        href_contains="median-unit",
        href_suffix=".xls",
    )
    if not hit:
        raise ValueError("Could not find VPSR unit download link")
    href, label = hit
    return href, label


async def ingest_vpsr_units():
    print("VPSR units: checking for quarterly data...")
    local = os.environ.get("VPSR_UNITS_XLS")
    mirror = (os.environ.get("VPSR_UNITS_URL") or "").strip()
    if local and os.path.isfile(local):
        filepath = os.path.abspath(local)
        label = os.path.basename(filepath)
        print(f"  Using local file: {filepath}")
    elif mirror:
        label = os.path.basename(mirror.split("?")[0]) or "mirror"
        print(f"  Using VPSR_UNITS_URL: {mirror[:100]}…")
        extra = (
            land_vic_download_headers(referer_catalogue_url=CATALOGUE_URL)
            if "land.vic.gov.au" in mirror.lower()
            else {}
        )
        async with ingestion_http_client() as client:
            resp = await client.get(mirror, timeout=120, headers=extra)
            resp.raise_for_status()
        filepath = "/tmp/vpsr_units_latest.xls"
        with open(filepath, "wb") as f:
            f.write(resp.content)
    else:
        download_url, label = await get_latest_unit_download_url()
        print(f"  Found: {label} → {download_url}")
        extra = (
            land_vic_download_headers(referer_catalogue_url=CATALOGUE_URL)
            if "land.vic.gov.au" in download_url.lower()
            else {}
        )
        async with ingestion_http_client() as client:
            resp = await client.get(download_url, timeout=120, headers=extra)
            resp.raise_for_status()
        filepath = "/tmp/vpsr_units_latest.xls"
        with open(filepath, "wb") as f:
            f.write(resp.content)

    records = parse_vpsr_xls(filepath)
    print(f"  Parsed {len(records)} suburbs")

    conn = await asyncpg.connect(_require_db_url(), statement_cache_size=0)
    updated = 0
    for r in records:
        prices = {
            k: v
            for k, v in r.items()
            if k not in ("suburb", "sales_volume") and v
        }
        if not prices:
            continue
        latest_col = sorted(prices.keys())[-1]
        latest_price = prices[latest_col]

        await conn.execute(
            """
            UPDATE suburbs SET
                unit_price_2023 = $2,
                data_updated_at = NOW()
            WHERE suburb = $1
        """,
            r["suburb"],
            latest_price,
        )
        updated += 1

    await conn.execute(
        """
        INSERT INTO ingestion_log (source, status, rows_upserted)
        VALUES ($1, 'success', $2)
    """,
        f"vpsr_units_{label}",
        updated,
    )

    await conn.close()
    print(f"  Applied unit medians to {updated} suburb rows (unit_price_2023)")


if __name__ == "__main__":
    from ingestion.project_env import load_project_dotenv

    load_project_dotenv()
    asyncio.run(ingest_vpsr_units())
