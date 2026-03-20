"""
CKAN (discover.data.vic.gov.au) helpers for VPSR house/unit packages.

Resource URLs still point at land.vic.gov.au; CKAN only 302s there. This module
is used to resolve the latest official XLS without HTML scraping.
"""
from __future__ import annotations

import httpx

from ingestion.fetch import BROWSER_HEADERS, land_vic_download_headers

CKAN_ACTION = "https://discover.data.vic.gov.au/api/3/action"

HOUSES_PACKAGE = "victorian-property-sales-report-median-house-by-suburb"
UNITS_PACKAGE = "victorian-property-sales-report-median-unit-by-suburb"

HOUSES_CATALOGUE_URL = f"https://discover.data.vic.gov.au/dataset/{HOUSES_PACKAGE}"
UNITS_CATALOGUE_URL = f"https://discover.data.vic.gov.au/dataset/{UNITS_PACKAGE}"


def ckan_client() -> httpx.Client:
    return httpx.Client(headers=BROWSER_HEADERS, follow_redirects=True, timeout=30)


def package_show(client: httpx.Client, package_id: str) -> dict:
    r = client.get(f"{CKAN_ACTION}/package_show", params={"id": package_id})
    r.raise_for_status()
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"package_show failed: {body}")
    return body["result"]


def pick_latest_land_vic_resource(
    resources: list,
    *,
    url_must_contain: str,
) -> dict:
    """Choose newest active resource whose URL is on land.vic and matches substring."""
    cands: list[dict] = []
    for res in resources:
        if (res.get("state") or "").lower() != "active":
            continue
        url = (res.get("url") or "").strip()
        if not url or "web.archive.org" in url.lower():
            continue
        if "land.vic.gov.au" not in url.lower():
            continue
        if url_must_contain.lower() not in url.lower():
            continue
        cands.append(res)
    if not cands:
        raise ValueError(
            f"No active land.vic resource matching {url_must_contain!r} in package"
        )

    def sort_key(res: dict) -> tuple[str, str]:
        return (res.get("release_date") or "", res.get("created") or "")

    return max(cands, key=sort_key)


def latest_houses_resource(client: httpx.Client) -> dict:
    pkg = package_show(client, HOUSES_PACKAGE)
    return pick_latest_land_vic_resource(pkg["resources"], url_must_contain="median-house")


def latest_units_resource(client: httpx.Client) -> dict:
    pkg = package_show(client, UNITS_PACKAGE)
    return pick_latest_land_vic_resource(pkg["resources"], url_must_contain="median-unit")


def download_land_vic_xls(
    client: httpx.Client,
    download_url: str,
    *,
    referer_catalogue_url: str,
) -> bytes:
    extra = land_vic_download_headers(referer_catalogue_url=referer_catalogue_url)
    headers = {**BROWSER_HEADERS, **extra}
    r = client.get(download_url, headers=headers, timeout=120)
    r.raise_for_status()
    return r.content
