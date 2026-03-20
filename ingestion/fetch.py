"""
HTTP helpers for ingestion. Vic gov CDNs sometimes return 403 to default Python clients;
use a browser-like User-Agent (still respect robots/terms; data is CC-BY).
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

# Shared headers for catalogue + file downloads from land.vic.gov.au / dffh.vic.gov.au
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}


def ingestion_http_client(**kwargs) -> httpx.AsyncClient:
    """AsyncClient configured for government file downloads."""
    headers = {**BROWSER_HEADERS, **kwargs.pop("headers", {})}
    return httpx.AsyncClient(headers=headers, follow_redirects=True, **kwargs)


def land_vic_download_headers(*, referer_catalogue_url: str) -> dict[str, str]:
    """
    land.vic.gov.au often returns 403 without a browser-like Referer from data.vic.
    Use when GETting direct __data/assets/...xls URLs discovered via CKAN.
    """
    return {
        "Referer": referer_catalogue_url,
        "Accept": "application/vnd.ms-excel,application/octet-stream,*/*;q=0.8",
    }


def first_ckan_go_to_resource(
    soup: BeautifulSoup,
    page_url: str,
    *,
    href_contains: str | None = None,
    href_suffix: str | None = None,
    href_predicate=None,
) -> tuple[str, str] | None:
    """
    CKAN/discover.data.vic often wraps 'Go to Resource' label in nested tags, so
    BeautifulSoup's a.string match fails. Match on get_text() instead.
    Returns (absolute_url, link_label) or None.
    """
    for a in soup.find_all("a", href=True):
        label = (a.get_text() or "").strip()
        if not re.search(r"go\s+to\s+resource", label, re.I):
            continue
        href = (a.get("href") or "").strip()
        if not href:
            continue
        href = urljoin(page_url, href)
        if href_contains and href_contains.lower() not in href.lower():
            continue
        if href_suffix and not href.lower().endswith(href_suffix.lower()):
            continue
        if href_predicate is not None and not href_predicate(href):
            continue
        return href, label
    return None
