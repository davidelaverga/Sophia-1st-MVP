"""add discord_id to users table

Revision ID: 3d8db1a9f9d2
Revises: fefc279c0f5b
Create Date: 2025-02-16 14:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3d8db1a9f9d2"
down_revision = "fefc279c0f5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("discord_id", sa.Text(), nullable=True))
    op.create_index(
        "uq_users_discord_id",
        "users",
        ["discord_id"],
        unique=True,
        postgresql_where=sa.text("discord_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_discord_id", table_name="users")
    op.drop_column("users", "discord_id")
