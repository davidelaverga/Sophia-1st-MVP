"""add rls policies

Revision ID: fefc279c0f5b
Revises: 202502110001
Create Date: 2025-10-31 16:40:38.717878
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "fefc279c0f5b"
down_revision = "202502110001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE emotion_scores ENABLE ROW LEVEL SECURITY;

        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'conversation_sessions'
                  AND policyname = 'conversation_sessions_service_role'
            ) THEN
                EXECUTE 'DROP POLICY conversation_sessions_service_role ON public.conversation_sessions';
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'conversation_sessions'
                  AND policyname = 'conversation_sessions_user_access'
            ) THEN
                EXECUTE 'DROP POLICY conversation_sessions_user_access ON public.conversation_sessions';
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'emotion_scores'
                  AND policyname = 'emotion_scores_service_role'
            ) THEN
                EXECUTE 'DROP POLICY emotion_scores_service_role ON public.emotion_scores';
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'emotion_scores'
                  AND policyname = 'emotion_scores_user_access'
            ) THEN
                EXECUTE 'DROP POLICY emotion_scores_user_access ON public.emotion_scores';
            END IF;
        END$$;

        CREATE POLICY conversation_sessions_service_role
            ON public.conversation_sessions
            FOR ALL
            USING ((auth.role() = 'service_role') OR (user_id = auth.uid()))
            WITH CHECK ((auth.role() = 'service_role') OR (user_id = auth.uid()));

        CREATE POLICY emotion_scores_service_role
            ON public.emotion_scores
            FOR ALL
            USING ((auth.role() = 'service_role') OR (user_id = auth.uid()))
            WITH CHECK ((auth.role() = 'service_role') OR (user_id = auth.uid()));

        CREATE POLICY conversation_sessions_user_access
            ON public.conversation_sessions
            FOR SELECT
            USING (user_id = auth.uid());

        CREATE POLICY emotion_scores_user_access
            ON public.emotion_scores
            FOR SELECT
            USING (user_id = auth.uid());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP POLICY IF EXISTS conversation_sessions_user_access ON public.conversation_sessions;
        DROP POLICY IF EXISTS conversation_sessions_service_role ON public.conversation_sessions;
        DROP POLICY IF EXISTS emotion_scores_user_access ON public.emotion_scores;
        DROP POLICY IF EXISTS emotion_scores_service_role ON public.emotion_scores;

        ALTER TABLE conversation_sessions DISABLE ROW LEVEL SECURITY;
        ALTER TABLE emotion_scores DISABLE ROW LEVEL SECURITY;
        """
    )
