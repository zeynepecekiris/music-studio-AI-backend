-- 0009: blocking users and reporting content (App Store guideline 1.2). Additive only.
CREATE TABLE IF NOT EXISTS user_blocks (
    blocker_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (blocker_id, blocked_id)
);
CREATE INDEX IF NOT EXISTS ix_user_blocks_blocked ON user_blocks (blocked_id);

CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR PRIMARY KEY,
    reporter_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(16) NOT NULL,          -- post | user | message | story | song
    target_id VARCHAR NOT NULL,
    target_user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    reason VARCHAR(32) NOT NULL,
    note TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'open',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_reports_target ON reports (target_type, target_id);
CREATE INDEX IF NOT EXISTS ix_reports_status ON reports (status, created_at);
