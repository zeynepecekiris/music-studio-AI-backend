-- 0005: song likes, quote posts, and an activity log that feeds Keşfet
-- Additive only.

CREATE TABLE IF NOT EXISTS song_likes (
  user_id    VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  song_id    VARCHAR NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, song_id)
);
CREATE INDEX IF NOT EXISTS ix_song_likes_song ON song_likes (song_id);

-- A post can quote another post or any public song, with your own words on top
ALTER TABLE wall_posts ADD COLUMN IF NOT EXISTS quote_post_id VARCHAR REFERENCES wall_posts(id) ON DELETE SET NULL;
ALTER TABLE wall_posts ADD COLUMN IF NOT EXISTS quote_song_id VARCHAR REFERENCES songs(id) ON DELETE SET NULL;

-- What people do that others can discover: likes and profile changes
CREATE TABLE IF NOT EXISTS activities (
  id         VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
  actor_id   VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind       VARCHAR(32) NOT NULL,   -- like_song | avatar | moved | visited | bio | genres
  song_id    VARCHAR REFERENCES songs(id) ON DELETE CASCADE,
  data       JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_activities_created ON activities (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_activities_actor ON activities (actor_id, created_at DESC);
