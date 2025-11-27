"""Split conversations into sessions and per-message rows for multi-turn chats."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202503070001"
down_revision = "202502110002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Extend conversation_sessions for continuous conversations ---
    op.add_column(
        "conversation_sessions",
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column(
            "status",
            sa.Text(),
            server_default="active",
            nullable=False,
        ),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column(
            "turn_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("last_intent", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("last_user_emotion_label", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("last_user_emotion_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("last_sophia_emotion_label", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("last_sophia_emotion_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("title", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column(
            "context_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )

    # Backfill new timestamps for existing rows
    op.execute(
        """
        UPDATE conversation_sessions
        SET
            started_at = COALESCE(started_at, created_at),
            last_activity_at = COALESCE(last_activity_at, updated_at),
            status = COALESCE(status, 'active'),
            turn_count = COALESCE(turn_count, 0),
            context_summary = COALESCE(context_summary, '{}'::jsonb)
        """
    )

    # Remove legacy single-turn columns now that per-message storage exists
    for column in [
        "context_memory",
        "intent",
        "audio_url",
        "sophia_emotion_confidence",
        "sophia_emotion_label",
        "user_emotion_confidence",
        "user_emotion_label",
        "reply",
        "transcript",
    ]:
        op.drop_column("conversation_sessions", column)

    # --- New conversation_messages table (one row per utterance) ---
    op.create_table(
        "conversation_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),  # user | sophia | system | tool
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.Column("input_type", sa.Text(), nullable=True),  # audio | text | system
        sa.Column("emotion_label", sa.Text(), nullable=True),
        sa.Column("emotion_confidence", sa.Float(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "turn_index", name="uq_conversation_messages_session_turn"
        ),
    )

    op.create_index(
        "ix_conversation_messages_session_id",
        "conversation_messages",
        ["session_id"],
    )
    op.create_index(
        "ix_conversation_messages_turn_index",
        "conversation_messages",
        ["turn_index"],
    )
    op.create_index(
        "ix_conversation_messages_created_at",
        "conversation_messages",
        ["created_at"],
    )

    # Reuse updated_at trigger for the new table
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_trigger
                WHERE tgname = 'conversation_messages_set_updated_at'
            ) THEN
                CREATE TRIGGER conversation_messages_set_updated_at
                BEFORE UPDATE ON conversation_messages
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END$$;
        """
    )

    # --- Link emotion_scores to conversation_messages (optional per turn) ---
    op.add_column(
        "emotion_scores",
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_emotion_scores_message_id",
        "emotion_scores",
        "conversation_messages",
        ["message_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_emotion_scores_message_id",
        "emotion_scores",
        ["message_id"],
    )


def downgrade() -> None:
    # Remove emotion_scores.message_id FK and column
    op.drop_index("ix_emotion_scores_message_id", table_name="emotion_scores")
    op.drop_constraint(
        "fk_emotion_scores_message_id",
        "emotion_scores",
        type_="foreignkey",
    )
    op.drop_column("emotion_scores", "message_id")

    # Drop updated_at trigger then table indices/table
    op.execute(
        "DROP TRIGGER IF EXISTS conversation_messages_set_updated_at ON conversation_messages"
    )
    op.drop_index("ix_conversation_messages_created_at", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_turn_index", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_session_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")

    # Remove added columns from conversation_sessions
    for column in [
        "context_summary",
        "title",
        "last_sophia_emotion_confidence",
        "last_sophia_emotion_label",
        "last_user_emotion_confidence",
        "last_user_emotion_label",
        "last_intent",
        "turn_count",
        "last_activity_at",
        "status",
        "ended_at",
        "started_at",
    ]:
        op.drop_column("conversation_sessions", column)

    # Re-add legacy single-turn columns
    op.add_column(
        "conversation_sessions", sa.Column("transcript", sa.Text(), nullable=True)
    )
    op.add_column("conversation_sessions", sa.Column("reply", sa.Text(), nullable=True))
    op.add_column(
        "conversation_sessions",
        sa.Column("user_emotion_label", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("user_emotion_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("sophia_emotion_label", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("sophia_emotion_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "conversation_sessions", sa.Column("audio_url", sa.Text(), nullable=True)
    )
    op.add_column("conversation_sessions", sa.Column("intent", sa.Text(), nullable=True))
    op.add_column(
        "conversation_sessions", sa.Column("context_memory", sa.Text(), nullable=True)
    )
