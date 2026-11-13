-- SerendibStay AI: additive hotel management migration.
-- Run only after reviewing the preflight results.
-- Existing 125 rows remain labelled 'legacy', NOT officially verified.
BEGIN;

-- Refuse to proceed if the legacy dataset is no longer the expected 125 rows.
DO $$
DECLARE
    total_count bigint;
    legacy_count bigint;
    existing_columns integer;
BEGIN
    SELECT COUNT(*) INTO total_count FROM hotels;
    SELECT COUNT(*) INTO legacy_count
    FROM hotels
    WHERE source IN (
      'Current public accommodation listing (2026)',
      'Sri Lanka Tourism / SLTDA indexed record (2026)'
    ) AND available IS TRUE;

    SELECT COUNT(*) INTO existing_columns
    FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'hotels'
      AND column_name IN ('verification_status', 'is_active');

    IF total_count <> 125 OR legacy_count <> 125 THEN
        RAISE EXCEPTION 'Migration stopped: expected exactly 125 original active hotels, found total %, matching %', total_count, legacy_count;
    END IF;
    IF existing_columns <> 0 THEN
        RAISE EXCEPTION 'Migration stopped: management columns already exist; inspect schema before retrying';
    END IF;
END $$;

ALTER TABLE hotels
ADD COLUMN verification_status VARCHAR NOT NULL DEFAULT 'pending';

ALTER TABLE hotels
ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE hotels
SET verification_status = 'legacy',
    is_active = TRUE
WHERE source IN (
    'Current public accommodation listing (2026)',
    'Sri Lanka Tourism / SLTDA indexed record (2026)'
)
AND available IS TRUE;

COMMIT;

-- Read-only verification after migration:
-- SELECT verification_status, is_active, COUNT(*) FROM hotels GROUP BY 1, 2;
