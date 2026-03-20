-- Plain-English UX fields (populated by ingestion scripts)
ALTER TABLE suburbs
  ADD COLUMN IF NOT EXISTS summary TEXT,
  ADD COLUMN IF NOT EXISTS score_label TEXT;
