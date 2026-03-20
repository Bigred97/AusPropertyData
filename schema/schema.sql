-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for suburb name fuzzy search

-- ================================================================
-- CORE TABLE: suburbs
-- 747 Victorian suburbs, 30 fields, all signals joined
-- ================================================================
CREATE TABLE suburbs (
    -- Identity
    suburb              TEXT PRIMARY KEY,
    postcode            TEXT NOT NULL,
    sa2_name            TEXT,
    is_metro            BOOLEAN NOT NULL DEFAULT false,

    -- Price history (from VPSR annual time series)
    price_2013          INTEGER,
    price_2014          INTEGER,
    price_2015          INTEGER,
    price_2016          INTEGER,
    price_2017          INTEGER,
    price_2018          INTEGER,
    price_2019          INTEGER,
    price_2020          INTEGER,
    price_2021          INTEGER,
    price_2022          INTEGER,
    price_2023          INTEGER,
    price_prelim_2024   INTEGER,
    growth_10yr         NUMERIC(6,1),     -- % growth 2013→2023
    growth_pa           NUMERIC(5,2),     -- annualised % growth

    -- Units (from VPSR units time series)
    unit_price_2023     INTEGER,
    unit_growth_10yr    NUMERIC(6,1),

    -- Yield (from DFFH rental report, Sep 2025)
    rent_3br_wk         INTEGER,          -- weekly median rent, 3br house
    rent_2br_wk         INTEGER,          -- weekly median rent, 2br flat
    gross_yield         NUMERIC(4,2),     -- (rent_3br_wk * 52 / price_2023) * 100

    -- Quarterly pulse (from latest VPSR quarterly file)
    price_q2_2024       INTEGER,
    price_q3_2024       INTEGER,
    price_q4_2024       INTEGER,
    price_q1_2025       INTEGER,
    price_q2_2025       INTEGER,
    sales_volume_q2_2025 INTEGER,         -- number of sales last quarter

    -- Census demographics (ABS 2021 G01, SAL level)
    population          INTEGER,
    pct_young_families  NUMERIC(4,1),     -- % aged 25-44
    pct_seniors         NUMERIC(4,1),     -- % aged 65+
    pct_children        NUMERIC(4,1),     -- % aged 0-14

    -- SEIFA 2021 (ABS, SAL level)
    irsd_score          NUMERIC(7,1),     -- disadvantage score (lower = more disadvantaged)
    irsd_decile         INTEGER,          -- 1=most disadvantaged, 10=most advantaged
    irsad_score         NUMERIC(7,1),     -- advantage+disadvantage score
    irsad_decile        INTEGER,
    ieo_score           NUMERIC(7,1),     -- education & occupation score
    ieo_decile          INTEGER,

    -- Transport (from PTV GTFS stops.txt, haversine calc)
    dist_to_station_km  NUMERIC(6,2),
    nearest_station     TEXT,

    -- VIF2023 population projections (Vic Planning, SA2 level)
    pop_growth_to_2031_pct  NUMERIC(6,1),
    pop_growth_to_2036_pct  NUMERIC(6,1),
    pop_2021_vif            INTEGER,
    pop_2036_projected      INTEGER,
    dw_growth_pct           NUMERIC(6,1),     -- dwelling supply growth to 2036
    projected_yf_pct_2036   NUMERIC(4,1),     -- projected % young families in 2036

    -- Investment scores (computed, stored for query performance)
    inv_score           NUMERIC(7,2),     -- composite investment score
    inv_profile         TEXT,             -- 'yield_hunter' | 'growth_chaser' | 'gentrification' | 'balanced'

    -- UX copy (filled by ingestion scripts)
    summary             TEXT,
    score_label         TEXT,

    -- Metadata
    data_updated_at     TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for all commonly filtered fields
CREATE INDEX idx_suburbs_postcode     ON suburbs(postcode);
CREATE INDEX idx_suburbs_price        ON suburbs(price_2023);
CREATE INDEX idx_suburbs_yield        ON suburbs(gross_yield);
CREATE INDEX idx_suburbs_growth       ON suburbs(growth_10yr);
CREATE INDEX idx_suburbs_irsd         ON suburbs(irsd_decile);
CREATE INDEX idx_suburbs_pop_growth   ON suburbs(pop_growth_to_2036_pct);
CREATE INDEX idx_suburbs_metro        ON suburbs(is_metro);
CREATE INDEX idx_suburbs_score        ON suburbs(inv_score);
CREATE INDEX idx_suburbs_name_trgm    ON suburbs USING gin(suburb gin_trgm_ops);
CREATE INDEX idx_suburbs_inv_profile  ON suburbs(inv_profile);

-- ================================================================
-- PRICE HISTORY TABLE
-- Normalized 11-year annual price series per suburb
-- Powers the price chart on suburb detail pages
-- ================================================================
CREATE TABLE suburb_price_history (
    id          SERIAL PRIMARY KEY,
    suburb      TEXT NOT NULL REFERENCES suburbs(suburb) ON DELETE CASCADE,
    year        INTEGER NOT NULL,
    median_price INTEGER,
    num_sales   INTEGER,
    property_type TEXT NOT NULL DEFAULT 'house',  -- 'house' | 'unit'
    UNIQUE(suburb, year, property_type)
);
CREATE INDEX idx_price_history_suburb ON suburb_price_history(suburb);

-- ================================================================
-- DATA INGESTION LOG
-- Track when each source was last updated
-- ================================================================
CREATE TABLE ingestion_log (
    id          SERIAL PRIMARY KEY,
    source      TEXT NOT NULL,            -- 'vpsr_q2_2025', 'dffh_sep_2025', etc.
    status      TEXT NOT NULL,            -- 'success' | 'error'
    rows_upserted INTEGER,
    error_message TEXT,
    run_at      TIMESTAMPTZ DEFAULT NOW()
);
