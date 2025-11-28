"""Create session_memory table for persisted session summaries."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202503200001"
down_revision = "202503070001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_memory",
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "topics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "turn_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "last_user_emotion",
            sa.Text(),
            server_default="neutral",
            nullable=False,
        ),
        sa.Column(
            "last_sophia_emotion",
            sa.Text(),
            server_default="neutral",
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
        sa.PrimaryKeyConstraint("session_id"),
    )

    op.create_index(
        "ix_session_memory_updated_at",
        "session_memory",
        ["updated_at"],
    )

    # Keep updated_at in sync with writes.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'session_memory_set_updated_at'
            ) THEN
                CREATE TRIGGER session_memory_set_updated_at
                BEFORE UPDATE ON session_memory
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END$$;
        """
    )

    # Enable RLS and restrict access to owning user or service role.
    op.execute("ALTER TABLE session_memory ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY session_memory_service_role
            ON session_memory FOR ALL
            USING (auth.role() = 'service_role')
            WITH CHECK (auth.role() = 'service_role');
        """
    )
    op.execute(
        """
        CREATE POLICY session_memory_user_select
            ON session_memory FOR SELECT
            USING (
                auth.role() = 'service_role'
                OR EXISTS (
                    SELECT 1
                    FROM conversation_sessions cs
                    WHERE cs.id = session_memory.session_id
                      AND cs.user_id = auth.uid()
                )
            );
        """
    )

    op.execute("GRANT ALL ON session_memory TO service_role;")
    op.execute("GRANT SELECT ON session_memory TO authenticated;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS session_memory_user_select ON session_memory;")
    op.execute("DROP POLICY IF EXISTS session_memory_service_role ON session_memory;")
    op.execute("ALTER TABLE session_memory DISABLE ROW LEVEL SECURITY;")

    op.execute(
        "DROP TRIGGER IF EXISTS session_memory_set_updated_at ON session_memory;"
    )
    op.drop_index("ix_session_memory_updated_at", table_name="session_memory")
    op.drop_table("session_memory")
