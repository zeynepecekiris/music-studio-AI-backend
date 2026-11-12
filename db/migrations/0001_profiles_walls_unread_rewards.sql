-- 0001: profiles, wall posts, mentions, unread messages, ad rewards
--
-- Additive only: no existing row is deleted. Existing rows only get values
-- for the new columns (last_message_at, read_at). Safe to run more than once.

-- ── Profiles (users table is the profile) ────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS favorite_genres TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_users_username_lower ON users (lower(username));
CREATE INDEX IF NOT EXISTS ix_users_display_name_lower ON users (lower(display_name));

-- ── Friendships: one row per pair, whichever direction ──────────────────────
CREATE INDEX IF NOT EXISTS ix_friendships_addressee_status ON friendships (addressee_id, status);
CREATE INDEX IF NOT EXISTS ix_friendships_requester_status ON friendships (requester_id, status);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM friendships
    GROUP BY LEAST(requester_id, addressee_id), GREATEST(requester_id, addressee_id)
    HAVING count(*) > 1
  ) THEN
    RAISE NOTICE 'Duplicate friendships exist; skipping uq_friendships_pair';
  ELSE
    CREATE UNIQUE INDEX IF NOT EXISTS uq_friendships_pair
      ON friendships (LEAST(requester_id, addressee_id), GREATEST(requester_id, addressee_id));
  END IF;
END $$;

-- ── Conversations: sort by last message, one conversation per pair ──────────
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_message_at TIMESTAMP;

UPDATE conversations c
SET last_message_at = COALESCE(
  (SELECT max(m.created_at) FROM messages m WHERE m.conversation_id = c.id),
  c.created_at
)
WHERE c.last_message_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_conversations_a_last ON conversations (user_a_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS ix_conversations_b_last ON conversations (user_b_id, last_message_at DESC);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM conversations
    GROUP BY LEAST(user_a_id, user_b_id), GREATEST(user_a_id, user_b_id)
    HAVING count(*) > 1
  ) THEN
    RAISE NOTICE 'Duplicate conversations exist; skipping uq_conversations_pair';
  ELSE
    CREATE UNIQUE INDEX IF NOT EXISTS uq_conversations_pair
      ON conversations (LEAST(user_a_id, user_b_id), GREATEST(user_a_id, user_b_id));
  END IF;
END $$;

-- ── Messages: unread tracking + paging ───────────────────────────────────────
ALTER TABLE messages ADD COLUMN IF NOT EXISTS read_at TIMESTAMP;

-- Messages sent before unread tracking existed count as read,
-- so nobody opens the app to a badge of hundreds of old messages.
UPDATE messages SET read_at = created_at WHERE read_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_messages_conv_created ON messages (conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_messages_unread ON messages (conversation_id, sender_id) WHERE read_at IS NULL;

-- ── Songs ────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS ix_songs_user_created ON songs (user_id, created_at DESC);

-- ── Wall posts ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS wall_posts (
  id            VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
  wall_owner_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  author_id     VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content       TEXT CHECK (char_length(content) <= 280),
  song_id       VARCHAR REFERENCES songs(id) ON DELETE SET NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT now(),
  deleted_at    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_wall_posts_owner_created
  ON wall_posts (wall_owner_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_wall_posts_author ON wall_posts (author_id);

CREATE TABLE IF NOT EXISTS post_mentions (
  id                VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
  post_id           VARCHAR NOT NULL REFERENCES wall_posts(id) ON DELETE CASCADE,
  mentioned_user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at        TIMESTAMP NOT NULL DEFAULT now(),
  CONSTRAINT uq_post_mentions UNIQUE (post_id, mentioned_user_id)
);

CREATE INDEX IF NOT EXISTS ix_post_mentions_user ON post_mentions (mentioned_user_id);

-- ── Rewarded ads ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ad_rewards (
  id             VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
  user_id        VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  reward_type    VARCHAR(32) NOT NULL CHECK (reward_type IN ('lyrics', 'add_friend')),
  transaction_id VARCHAR UNIQUE,          -- AdMob server-side verification id
  verified       BOOLEAN NOT NULL DEFAULT FALSE,
  consumed_at    TIMESTAMP,
  created_at     TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ad_rewards_user_type ON ad_rewards (user_id, reward_type, created_at DESC);
