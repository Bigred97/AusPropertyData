-- Add columns if they don't exist (schema.sql already has them; this is for existing DBs)
ALTER TABLE suburbs ADD COLUMN IF NOT EXISTS unit_price_2023 INTEGER;
ALTER TABLE suburbs ADD COLUMN IF NOT EXISTS price_q2_2025 INTEGER;
ALTER TABLE suburbs ADD COLUMN IF NOT EXISTS sales_volume_q2_2025 INTEGER;
