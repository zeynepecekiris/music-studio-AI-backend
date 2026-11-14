-- 0007: separated stems (drums, bass, vocals, ...) for the in-app mixer. Additive only.
ALTER TABLE songs ADD COLUMN IF NOT EXISTS stems JSONB;
ALTER TABLE songs ADD COLUMN IF NOT EXISTS stems_status VARCHAR(16);
