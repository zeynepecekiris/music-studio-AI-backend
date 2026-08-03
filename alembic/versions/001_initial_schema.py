"""initial schema: users, songs, friendships, conversations, messages

Revision ID: 001
Revises:
Create Date: 2026-08-01
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('username', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'songs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('audio_url', sa.String(), nullable=False),
        sa.Column('cover_art_url', sa.String(), nullable=True),
        sa.Column('lyrics', sa.Text(), nullable=True),
        sa.Column('genre', sa.String(), nullable=True),
        sa.Column('mood', sa.String(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('is_public', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'friendships',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('requester_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('addressee_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('status', sa.Enum('pending', 'accepted', 'blocked', name='friendshipstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'conversations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_a_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('user_b_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'messages',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('conversation_id', sa.String(), sa.ForeignKey('conversations.id'), nullable=False, index=True),
        sa.Column('sender_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('song_id', sa.String(), sa.ForeignKey('songs.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('friendships')
    op.drop_table('songs')
    op.drop_table('users')
