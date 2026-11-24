-- 0010: likes and comments on any feed item. Additive only.
--   target_type: post | song | story | activity
-- Songs keep their own song_likes table; feed_likes covers the rest
-- (text posts, profile changes, clips).
CREATE TABLE IF NOT EXISTS feed_likes (
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(16) NOT NULL,
    target_id VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, target_type, target_id)
);
CREATE INDEX IF NOT EXISTS ix_feed_likes_target ON feed_likes (target_type, target_id);

CREATE TABLE IF NOT EXISTS comments (
    id VARCHAR PRIMARY KEY,
    target_type VARCHAR(16) NOT NULL,
    target_id VARCHAR NOT NULL,
    target_owner_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    author_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_comments_target ON comments (target_type, target_id, created_at);
CREATE INDEX IF NOT EXISTS ix_comments_author ON comments (author_id);
