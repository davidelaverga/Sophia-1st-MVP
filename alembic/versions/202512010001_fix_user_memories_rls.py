"""Fix user_memories RLS policies for proper data isolation (Task #42919)

Revision ID: 202512010001
Revises: 202503200001
Create Date: 2025-12-01
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "202512010001"
down_revision = "202503200001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix RLS policies to ensure user data isolation.

    Previous policies used USING(true) which allowed any authenticated user
    to read/modify all records. New policies check auth.uid()::text = user_id.
    """
    op.execute("""
        -- Drop old permissive policies
        DROP POLICY IF EXISTS "Allow all" ON user_memories;
        DROP POLICY IF EXISTS "Users can view own memories" ON user_memories;
        DROP POLICY IF EXISTS "Service role can insert memories" ON user_memories;
        DROP POLICY IF EXISTS "Service role can update memories" ON user_memories;
        DROP POLICY IF EXISTS "Service role can delete memories" ON user_memories;

        -- Create new policies with proper user isolation
        CREATE POLICY "Users can view own memories"
            ON user_memories FOR SELECT
            USING (auth.uid()::text = user_id);

        CREATE POLICY "Users can insert own memories"
            ON user_memories FOR INSERT
            WITH CHECK (auth.uid()::text = user_id);

        CREATE POLICY "Users can update own memories"
            ON user_memories FOR UPDATE
            USING (auth.uid()::text = user_id);

        CREATE POLICY "Users can delete own memories"
            ON user_memories FOR DELETE
            USING (auth.uid()::text = user_id);

        -- Also allow service_role full access for backend operations
        CREATE POLICY "Service role full access"
            ON user_memories FOR ALL
            USING (auth.role() = 'service_role')
            WITH CHECK (auth.role() = 'service_role');
    """)


def downgrade() -> None:
    """Revert to original permissive policies (NOT RECOMMENDED)."""
    op.execute("""
        DROP POLICY IF EXISTS "Users can view own memories" ON user_memories;
        DROP POLICY IF EXISTS "Users can insert own memories" ON user_memories;
        DROP POLICY IF EXISTS "Users can update own memories" ON user_memories;
        DROP POLICY IF EXISTS "Users can delete own memories" ON user_memories;
        DROP POLICY IF EXISTS "Service role full access" ON user_memories;

        -- Restore original (insecure) policies
        CREATE POLICY "Users can view own memories"
            ON user_memories FOR SELECT
            USING (true);

        CREATE POLICY "Service role can insert memories"
            ON user_memories FOR INSERT
            WITH CHECK (true);

        CREATE POLICY "Service role can update memories"
            ON user_memories FOR UPDATE
            USING (true);

        CREATE POLICY "Service role can delete memories"
            ON user_memories FOR DELETE
            USING (true);
    """)
