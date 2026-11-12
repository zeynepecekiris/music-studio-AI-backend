-- 0004: international profile (where you're from, where you've been, languages)
-- Additive only; existing users simply have these empty.

ALTER TABLE users ADD COLUMN IF NOT EXISTS country_code      VARCHAR(2);
ALTER TABLE users ADD COLUMN IF NOT EXISTS city              VARCHAR(60);
-- city folded for matching: İstanbul / Istanbul / istanbul, München / Munchen
ALTER TABLE users ADD COLUMN IF NOT EXISTS city_key          VARCHAR(60);
ALTER TABLE users ADD COLUMN IF NOT EXISTS visited_countries TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS languages         TEXT[] NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS ix_users_country_city ON users (country_code, city_key);
