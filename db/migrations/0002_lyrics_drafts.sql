-- 0002: lyrics drafts, so lyrics written/edited in the app live on the server
-- Additive only.

CREATE TABLE IF NOT EXISTS lyrics_drafts (
  id         VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
  user_id    VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title      VARCHAR(120),
  story      TEXT,
  theme      VARCHAR(40),
  lyrics     TEXT NOT NULL CHECK (char_length(lyrics) <= 10000),
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_lyrics_drafts_user_updated ON lyrics_drafts (user_id, updated_at DESC);
