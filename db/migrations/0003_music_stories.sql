-- 0003: music stories (Instagram-like, 24h) built on the user's own songs
-- Additive only.

CREATE TABLE IF NOT EXISTS music_stories (
  id         VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
  user_id    VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  song_id    VARCHAR NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
  caption    VARCHAR(150),
  style      VARCHAR(32) NOT NULL DEFAULT 'neon',
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  expires_at TIMESTAMP NOT NULL DEFAULT (now() + interval '24 hours')
);

CREATE INDEX IF NOT EXISTS ix_music_stories_user_created ON music_stories (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_music_stories_expires ON music_stories (expires_at);

CREATE TABLE IF NOT EXISTS story_views (
  story_id  VARCHAR NOT NULL REFERENCES music_stories(id) ON DELETE CASCADE,
  viewer_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  viewed_at TIMESTAMP NOT NULL DEFAULT now(),
  PRIMARY KEY (story_id, viewer_id)
);

CREATE INDEX IF NOT EXISTS ix_story_views_viewer ON story_views (viewer_id);
