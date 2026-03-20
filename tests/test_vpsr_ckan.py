"""vpsr_ckan resource selection (no network)."""

from ingestion.vpsr_ckan import pick_latest_land_vic_resource


def test_pick_latest_by_release_date():
    resources = [
        {
            "state": "active",
            "url": "https://www.land.vic.gov.au/old.xls",
            "release_date": "2024-01-01",
            "created": "2024-01-01",
        },
        {
            "state": "active",
            "url": "https://www.land.vic.gov.au/median-house-q2-2025.xls",
            "release_date": "2025-12-02",
            "created": "2025-12-02",
        },
    ]
    got = pick_latest_land_vic_resource(resources, url_must_contain="median-house")
    assert "median-house-q2-2025" in got["url"]


def test_skips_archive_and_inactive():
    resources = [
        {
            "state": "inactive",
            "url": "https://www.land.vic.gov.au/median-house-a.xls",
            "release_date": "2025-12-02",
            "created": "x",
        },
        {
            "state": "active",
            "url": "https://web.archive.org/web/1/https://www.land.vic.gov.au/median-house-b.xls",
            "release_date": "2026-01-01",
            "created": "x",
        },
        {
            "state": "active",
            "url": "https://www.land.vic.gov.au/median-house-c.xls",
            "release_date": "2024-06-01",
            "created": "x",
        },
    ]
    got = pick_latest_land_vic_resource(resources, url_must_contain="median-house")
    assert got["url"].endswith("median-house-c.xls")
