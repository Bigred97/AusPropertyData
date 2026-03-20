# AussiePropertyData — Verified Data Sources

**Last verified:** March 2026  
**All links tested live. Do not guess — always go to the catalogue page first, then click "Go to Resource".**

---

## HOW TO UPDATE EACH QUARTER (3 files, ~30 mins total)

### Step 1 — House prices

1. Go to: https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-house-by-suburb
2. The current file is shown under "Data and Resources" — click **"Go to Resource"**
3. Save as `median-house-QQUARTER-YEAR.xls` (e.g. `median-house-q3-2025.xls`)
4. Run: `python -m ingestion.vpsr_houses`  
   **Or** set `VPSR_HOUSES_XLS=/path/to/median-house-q2-2025.xls` to skip HTTP download (recommended — see note on 403 below).

**Historical releases** (if you need to backfill):  
https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-house-by-suburb/historical

| Quarter | Verified Direct URL | Status |
|---------|-------------------|--------|
| Q2 2025 (Jun) — CURRENT | https://www.land.vic.gov.au/__data/assets/excel_doc/0023/762143/median-house-q2-2025.xls | ✅ Live |
| Q3 2024 (Sep) | https://www.land.vic.gov.au/__data/assets/excel_doc/0034/739294/vpsr-median-house-q3-2024.xls | ✅ Live |
| Q2 2024 (Jun) | https://www.land.vic.gov.au/__data/assets/excel_doc/0029/728057/Median-House-2nd-Qtr-2024.xls | ✅ Live |
| Q1 2024 (Mar) | https://www.land.vic.gov.au/__data/assets/excel_doc/0021/716052/Median-House-VGS-1st-Qtr-2024.xls | ✅ Live |

> **Note on Q3 2025:** The catalogue page shows "June 2025 Quarter" as current as of March 2026.  
> The September 2025 quarter data was announced but the direct XLS URL was not yet listed on the  
> catalogue page at time of verification. Check the catalogue page — it will appear there when published.

---

### Step 2 — Unit prices

1. Go to: https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-unit-by-suburb
2. Click **"Go to Resource"** on the current file
3. Save as `median-unit-QQUARTER-YEAR.xls`
4. Run: `python -m ingestion.vpsr_units`  
   **Or** set `VPSR_UNITS_XLS=/path/to/median-unit-q2-2025.xls`.

| Quarter | Verified Direct URL | Status |
|---------|-------------------|--------|
| Q2 2025 (Jun) — CURRENT | https://www.land.vic.gov.au/__data/assets/excel_doc/0025/762145/median-unit-q2-2025.xls | ✅ Live |

---

### Step 3 — Rental yields by suburb

1. Go to: https://discover.data.vic.gov.au/dataset/rental-report-quarterly-moving-annual-rents-by-suburb
2. The CURRENT file is listed at the top — click **"Go to Resource"**
3. Save as `moving-annual-rent-suburb-QUARTER-YEAR.xlsx`
4. Run: `python -m ingestion.dffh_rental`  
   **Or** set `DFFH_RENTAL_XLSX=/path/to/file.xlsx` to use a browser-downloaded workbook.

**Historical releases:**  
https://discover.data.vic.gov.au/dataset/rental-report-quarterly-moving-annual-rents-by-suburb/historical

| Quarter | Verified Direct URL | Status |
|---------|-------------------|--------|
| Sep 2025 — CURRENT (most recent) | https://www.dffh.vic.gov.au/moving-annual-rent-suburb-september-quarter-2025-excel | ✅ Live |
| Jun 2025 | https://www.dffh.vic.gov.au/moving-annual-rent-suburb-june-quarter-2025-excel | ✅ Live |
| Mar 2025 | https://www.dffh.vic.gov.au/moving-annual-rent-suburb-march-quarter-2025-excel | ✅ Live |
| Dec 2024 | https://www.dffh.vic.gov.au/moving-annual-rent-suburb-december-quarter-2024-excel | ✅ Live |

> **Note:** DFFH URLs follow a consistent pattern:  
> `https://www.dffh.vic.gov.au/moving-annual-rent-suburb-[month]-quarter-[year]-excel`  
> e.g. next one will be: `https://www.dffh.vic.gov.au/moving-annual-rent-suburb-december-quarter-2025-excel`  
> Always confirm on the catalogue page first before using a guessed URL.

---

### Step 4 — After all 3 files loaded

Run: `python -m ingestion.recompute_scores`

---

## Automation (GitHub Actions)

Releases **don’t land on a fixed day**, so CI **polls** on a schedule (weekly + mid-month). When the catalogue shows a new file, the next successful job ingests it.

The workflow runs **DFFH rental first** (usually downloads OK), then **VPSR houses/units**. If **`land.vic.gov.au` returns 403** on the runner, set optional repo secrets **`VPSR_HOUSES_URL`** and **`VPSR_UNITS_URL`** to HTTPS URLs of the same `.xls` files (e.g. raw links from a GitHub Release after you upload the official files).

Details: **[docs/AUTOMATION.md](AUTOMATION.md)** — secrets, cron rationale, and 403 fallbacks.

---

## SET AND FORGET — update only when new release announced

### House price 10-year time series (annual, not quarterly)

- **Catalogue:** https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-house-by-suburb-time-series
- **Current file:** Houses-by-suburb-2013-2023.xlsx
- **Direct URL:** https://www.land.vic.gov.au/__data/assets/excel_doc/0029/709751/Houses-by-suburb-2013-2023.xlsx ✅
- **Next update:** When VGV publishes a 2014–2024 file — check catalogue annually

### ABS Census 2021 — demographics (population, young families, seniors, children)

- **Catalogue:** https://www.abs.gov.au/census/find-census-data/datapacks
- Navigate: 2021 → Community Profiles → SAL → VIC → download G01
- **Next update:** 2026 Census data, released ~2027

### ABS SEIFA 2021 — socioeconomic index

- **Catalogue:** https://www.abs.gov.au/statistics/people/people-and-communities/socio-economic-indexes-areas-seifa-australia/latest-release
- Scroll to "Data downloads" → SAL Excel file
- **Next update:** ~2027

### VIF2023 — population projections to 2036

- **Catalogue:** https://www.planning.vic.gov.au/land-use-and-population-research/victoria-in-future
- **Direct URL:** https://www.planning.vic.gov.au/__data/assets/excel_doc/0028/691660/VIF2023_SA2_Pop_Hhold_Dwelling_Projections_to_2036_Release_2.xlsx ✅
- **Next update:** VIF2026 expected late 2026 — check planning.vic.gov.au

### PTV GTFS — train/tram station locations

- **Catalogue:** https://discover.data.vic.gov.au/dataset/ptv-metro-timetable-data-gtfs-zip-file-update
- Download the ZIP, extract stops.txt
- **Update:** Only needed when new stations open — check annually

### ABS ASGS concordance — suburb to SA2 join key

- **Catalogue:** https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/allocation-files
- **Next update:** 2026 ASGS edition — stable until then

---

## QUARTERLY RELEASE CALENDAR

| Quarter ends | VGV publishes VPSR | DFFH publishes rental |
|-------------|-------------------|----------------------|
| 31 March    | ~June/July         | ~June                |
| 30 June     | ~September/October | ~September           |
| 30 September| ~December/January  | ~December            |
| 31 December | ~March/April       | ~March               |

> VGV typically releases about 3 months after quarter end.  
> DFFH typically releases about 2-3 months after quarter end.  
> Always check the catalogue page — don't rely on a fixed schedule.

---

## IMPORTANT NOTES FOR DEVELOPER

1. **Always go to the catalogue page first.** Direct URLs to land.vic.gov.au change with each new release.  
   The catalogue page always shows the current file — copy the URL from "Go to Resource" there.

2. **DFFH rental URLs follow a pattern** but always verify before using. The catalogue historical page  
   at https://discover.data.vic.gov.au/dataset/rental-report-quarterly-moving-annual-rents-by-suburb/historical  
   lists every release with confirmed working URLs.

3. **Dec 2025 quarterly rental data is not yet published** as of March 2026. Sep 2025 is the most current.  
   When Dec 2025 is published, the URL will appear at the catalogue page.

4. **land.vic.gov.au often blocks direct HTTP requests** (e.g. 403) from servers/scripts. Prefer:  
   download via browser, then run ingestion with **`VPSR_HOUSES_XLS`** / **`VPSR_UNITS_XLS`** pointing at the saved file.  
   Catalogue page scraping for the link may still work; the actual file fetch may not.

5. **Licence:** All sources are CC-BY 4.0. Attribution required: *Source: Valuer-General Victoria /  
   Homes Victoria / ABS / PTV / Department of Transport and Planning, Victorian Government*
