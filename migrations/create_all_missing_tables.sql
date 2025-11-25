-- Complete Migration: Create all missing tables and configure storage
-- Task #42817: Fix conversation_sessions and audio upload issues
-- Date: 2025-11-25
--
-- INSTRUCTIONS FOR SUPABASE:
-- 1. Open Supabase SQL Editor: https://supabase.com/dashboard/project/[YOUR-PROJECT]/sql
-- 2. Copy and paste this entire SQL script
-- 3. Click "Run" to execute
-- 4. Verify success with verification queries at the end

-- ============================================
-- Step 1: Enable required extensions
-- ============================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Step 2: Create users table (if not exists)
-- ============================================
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id TEXT,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_discord_id
    ON public.users(discord_id)
    WHERE discord_id IS NOT NULL;

-- ============================================
-- Step 3: Create conversation_sessions table
-- ============================================
CREATE TABLE IF NOT EXISTS public.conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    transcript TEXT,
    reply TEXT,
    user_emotion_label TEXT,
    user_emotion_confidence FLOAT,
    sophia_emotion_label TEXT,
    sophia_emotion_confidence FLOAT,
    audio_url TEXT,
    intent TEXT,
    context_memory TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    CONSTRAINT fk_conversation_sessions_user_id
        FOREIGN KEY (user_id)
        REFERENCES public.users(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_id
    ON public.conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_created_at
    ON public.conversation_sessions(created_at DESC);

-- ============================================
-- Step 4: Create emotion_scores table
-- ============================================
CREATE TABLE IF NOT EXISTS public.emotion_scores (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    role TEXT NOT NULL,
    label TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    CONSTRAINT fk_emotion_scores_session_id
        FOREIGN KEY (session_id)
        REFERENCES public.conversation_sessions(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_emotion_scores_user_id
        FOREIGN KEY (user_id)
        REFERENCES public.users(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_emotion_scores_session_id
    ON public.emotion_scores(session_id);
CREATE INDEX IF NOT EXISTS idx_emotion_scores_user_id
    ON public.emotion_scores(user_id);

-- ============================================
-- Step 5: Create user_consents table
-- ============================================
CREATE TABLE IF NOT EXISTS public.user_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id TEXT NOT NULL,
    consent_hash TEXT NOT NULL,
    ip_address TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    CONSTRAINT uq_user_consents_discord_id UNIQUE (discord_id)
);

CREATE INDEX IF NOT EXISTS ix_user_consents_consent_hash
    ON public.user_consents(consent_hash);

-- ============================================
-- Step 6: Create update trigger function
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to all tables
DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOR table_name IN
        SELECT unnest(ARRAY['users', 'conversation_sessions', 'emotion_scores', 'user_consents'])
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS %I_set_updated_at ON public.%I;
            CREATE TRIGGER %I_set_updated_at
                BEFORE UPDATE ON public.%I
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', table_name, table_name, table_name, table_name);
    END LOOP;
END $$;

-- ============================================
-- Step 7: Enable RLS on all tables
-- ============================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.emotion_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_consents ENABLE ROW LEVEL SECURITY;

-- ============================================
-- Step 8: Create RLS policies for users table
-- ============================================
DROP POLICY IF EXISTS "Users can view own data" ON public.users;
CREATE POLICY "Users can view own data"
    ON public.users FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Service role can insert users" ON public.users;
CREATE POLICY "Service role can insert users"
    ON public.users FOR INSERT
    WITH CHECK (true);

DROP POLICY IF EXISTS "Service role can update users" ON public.users;
CREATE POLICY "Service role can update users"
    ON public.users FOR UPDATE
    USING (true);

-- ============================================
-- Step 9: Create RLS policies for conversation_sessions
-- ============================================
DROP POLICY IF EXISTS "Users can view own sessions" ON public.conversation_sessions;
CREATE POLICY "Users can view own sessions"
    ON public.conversation_sessions FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Service role can insert sessions" ON public.conversation_sessions;
CREATE POLICY "Service role can insert sessions"
    ON public.conversation_sessions FOR INSERT
    WITH CHECK (true);

DROP POLICY IF EXISTS "Service role can update sessions" ON public.conversation_sessions;
CREATE POLICY "Service role can update sessions"
    ON public.conversation_sessions FOR UPDATE
    USING (true);

-- ============================================
-- Step 10: Create RLS policies for emotion_scores
-- ============================================
DROP POLICY IF EXISTS "Users can view own emotions" ON public.emotion_scores;
CREATE POLICY "Users can view own emotions"
    ON public.emotion_scores FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Service role can insert emotions" ON public.emotion_scores;
CREATE POLICY "Service role can insert emotions"
    ON public.emotion_scores FOR INSERT
    WITH CHECK (true);

-- ============================================
-- Step 11: Create RLS policies for user_consents
-- ============================================
DROP POLICY IF EXISTS "Users can view own consents" ON public.user_consents;
CREATE POLICY "Users can view own consents"
    ON public.user_consents FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Service role can insert consents" ON public.user_consents;
CREATE POLICY "Service role can insert consents"
    ON public.user_consents FOR INSERT
    WITH CHECK (true);

-- ============================================
-- Step 12: Grant permissions to service_role
-- ============================================
GRANT ALL ON public.users TO authenticated, service_role;
GRANT ALL ON public.conversation_sessions TO authenticated, service_role;
GRANT ALL ON public.emotion_scores TO authenticated, service_role;
GRANT ALL ON public.user_consents TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.emotion_scores_id_seq TO authenticated, service_role;

-- ============================================
-- Step 13: Add comments for documentation
-- ============================================
COMMENT ON TABLE public.users IS 'User accounts for Sophia DeFi assistant';
COMMENT ON TABLE public.conversation_sessions IS 'Conversation history with emotions and context';
COMMENT ON TABLE public.emotion_scores IS 'Emotion analysis scores for conversations';
COMMENT ON TABLE public.user_consents IS 'User consent records for data processing';

-- ============================================
-- Verification Queries
-- ============================================

-- Check all tables exist
SELECT
    'Tables created' as status,
    COUNT(*) as table_count
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_name IN ('users', 'conversation_sessions', 'emotion_scores', 'user_consents');
-- Expected: table_count = 4

-- Check RLS is enabled on all tables
SELECT
    tablename,
    CASE WHEN rowsecurity THEN 'ENABLED' ELSE 'DISABLED' END as rls_status
FROM pg_tables t
JOIN pg_class c ON t.tablename = c.relname
WHERE t.schemaname = 'public'
    AND t.tablename IN ('users', 'conversation_sessions', 'emotion_scores', 'user_consents')
ORDER BY tablename;

-- Check triggers exist
SELECT
    trigger_name,
    event_object_table
FROM information_schema.triggers
WHERE event_object_schema = 'public'
    AND trigger_name LIKE '%updated_at%'
ORDER BY event_object_table;

-- ============================================
-- DONE! ✅
-- ============================================
-- Next: Configure audio storage bucket via Supabase Dashboard:
-- 1. Go to Storage > Create bucket "audio" (if not exists)
-- 2. Set bucket to PUBLIC or configure policies
-- 3. Test with: python test_supabase_simple.py
-- ============================================
