-- 0008: a wall post can be a music clip (the song played over the clip visuals). Additive only.
ALTER TABLE wall_posts ADD COLUMN IF NOT EXISTS is_clip BOOLEAN NOT NULL DEFAULT FALSE;
