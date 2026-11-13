-- 0006: Expo push tokens, one row per device. Additive only.

CREATE TABLE IF NOT EXISTS push_tokens (
  token      VARCHAR PRIMARY KEY,
  user_id    VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  platform   VARCHAR(16),
  language   VARCHAR(8),
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_push_tokens_user ON push_tokens (user_id);
