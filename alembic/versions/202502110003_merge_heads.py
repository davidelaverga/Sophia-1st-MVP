"""Merge heads 202502110002 and 3d8db1a9f9d2 into a single lineage."""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "202502110003"
down_revision = ("202502110002", "3d8db1a9f9d2")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op merge migration."""
    pass


def downgrade() -> None:
    """No-op downgrade; cannot un-merge branches."""
    pass
