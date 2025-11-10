"""Initial schema for Supabase conversation and consent tracking."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202502110001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "conversation_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("reply", sa.Text(), nullable=True),
        sa.Column("user_emotion_label", sa.Text(), nullable=True),
        sa.Column("user_emotion_confidence", sa.Float(), nullable=True),
        sa.Column("sophia_emotion_label", sa.Text(), nullable=True),
        sa.Column("sophia_emotion_confidence", sa.Float(), nullable=True),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.Column("context_memory", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversation_sessions_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "emotion_scores",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["conversation_sessions.id"],
            name="fk_emotion_scores_session_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_emotion_scores_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_consents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("discord_id", sa.Text(), nullable=False),
        sa.Column("consent_hash", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
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
        sa.UniqueConstraint("discord_id", name="uq_user_consents_discord_id"),
    )
    op.create_index(
        "ix_user_consents_consent_hash",
        "user_consents",
        ["consent_hash"],
        unique=False,
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    for table_name in (
        "users",
        "conversation_sessions",
        "emotion_scores",
        "user_consents",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table_name}_set_updated_at
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            """
        )


def downgrade() -> None:
    for table_name in (
        "user_consents",
        "emotion_scores",
        "conversation_sessions",
        "users",
    ):
        op.execute(
            f"DROP TRIGGER IF EXISTS {table_name}_set_updated_at ON {table_name}"
        )

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column")

    op.drop_index("ix_user_consents_consent_hash", table_name="user_consents")
    op.drop_table("user_consents")
    op.drop_table("emotion_scores")
    op.drop_table("conversation_sessions")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
