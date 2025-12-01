-- Enable Row-Level Security and define policies for conversation-centric tables.
-- Run this script in the Supabase SQL editor with the service role.

BEGIN;

-- Enable RLS on core tables
ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE emotion_scores ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist to avoid duplication
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'conversation_sessions' AND policyname = 'conversation_sessions_service_role') THEN
        EXECUTE 'DROP POLICY conversation_sessions_service_role ON public.conversation_sessions';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'conversation_sessions' AND policyname = 'conversation_sessions_user_access') THEN
        EXECUTE 'DROP POLICY conversation_sessions_user_access ON public.conversation_sessions';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'emotion_scores' AND policyname = 'emotion_scores_service_role') THEN
        EXECUTE 'DROP POLICY emotion_scores_service_role ON public.emotion_scores';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'emotion_scores' AND policyname = 'emotion_scores_user_access') THEN
        EXECUTE 'DROP POLICY emotion_scores_user_access ON public.emotion_scores';
    END IF;
END$$;

-- Service role (backend) retains full access for inserts/selects/updates
CREATE POLICY conversation_sessions_service_role
    ON public.conversation_sessions
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY emotion_scores_service_role
    ON public.emotion_scores
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- End-user access: can read/write only their own rows
CREATE POLICY conversation_sessions_user_access
    ON public.conversation_sessions
    FOR SELECT USING (user_id::text = auth.uid())
    WITH CHECK (user_id::text = auth.uid());

CREATE POLICY emotion_scores_user_access
    ON public.emotion_scores
    FOR SELECT USING (user_id::text = auth.uid())
    WITH CHECK (user_id::text = auth.uid());

COMMIT;
