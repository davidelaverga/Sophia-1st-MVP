-- Migration: Create user_memories table for MemO semantic memory storage
-- Task #42817: Fix Mem0 database schema error
-- Date: 2025-11-25
--
-- INSTRUCTIONS FOR SUPABASE:
-- 1. Open your Supabase project: https://supabase.com/dashboard/project/[YOUR-PROJECT]/sql
-- 2. Click "SQL Editor" in the left sidebar
-- 3. Create a new query
-- 4. Copy and paste this entire SQL script
-- 5. Click "Run" to execute
-- 6. Verify success: SELECT * FROM user_memories LIMIT 1;

-- ============================================
-- Step 1: Enable pgvector extension
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Step 2: Create user_memories table
-- ============================================
CREATE TABLE IF NOT EXISTS public.user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,  -- Changed from UUID to TEXT to match app/services/memo.py:111
    session_id UUID,
    memory_text TEXT NOT NULL,
    embedding vector(384),  -- pgvector type for all-MiniLM-L6-v2 (384 dimensions)
    memory_type TEXT DEFAULT 'context',
    importance FLOAT DEFAULT 0.5,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_importance CHECK (importance >= 0.0 AND importance <= 1.0),
    CONSTRAINT valid_memory_type CHECK (memory_type IN ('context', 'preference', 'emotion', 'fact'))
);

-- ============================================
-- Step 3: Create indexes for efficient queries
-- ============================================

-- Index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_user_memories_user_id
    ON public.user_memories(user_id);

-- Index for session_id lookups
CREATE INDEX IF NOT EXISTS idx_user_memories_session_id
    ON public.user_memories(session_id);

-- Index for recent memories (sorted by created_at)
CREATE INDEX IF NOT EXISTS idx_user_memories_created_at
    ON public.user_memories(created_at DESC);

-- Index for memory type filtering
CREATE INDEX IF NOT EXISTS idx_user_memories_memory_type
    ON public.user_memories(memory_type);

-- ============================================
-- Step 4: Create vector index for similarity search
-- ============================================

-- IVFFlat index for vector similarity search using cosine distance
-- For < 1M rows: lists = rows / 1000 (we use 100 as conservative estimate)
-- For > 1M rows: lists = sqrt(rows)
CREATE INDEX IF NOT EXISTS idx_user_memories_embedding_ivfflat
    ON public.user_memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Alternative: HNSW index (faster but uses more memory)
-- Uncomment below and comment out IVFFlat above if you prefer HNSW:
-- CREATE INDEX IF NOT EXISTS idx_user_memories_embedding_hnsw
--     ON public.user_memories
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

-- ============================================
-- Step 5: Create trigger for auto-updating updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_user_memories_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_user_memories_updated_at
    BEFORE UPDATE ON public.user_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_user_memories_updated_at();

-- ============================================
-- Step 6: Enable Row Level Security (RLS)
-- ============================================

ALTER TABLE public.user_memories ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all reads (can be restricted later based on auth)
CREATE POLICY "Users can view own memories"
    ON public.user_memories
    FOR SELECT
    USING (true);

-- Policy: Service role can insert memories
CREATE POLICY "Service role can insert memories"
    ON public.user_memories
    FOR INSERT
    WITH CHECK (true);

-- Policy: Service role can update memories
CREATE POLICY "Service role can update memories"
    ON public.user_memories
    FOR UPDATE
    USING (true);

-- Policy: Service role can delete memories
CREATE POLICY "Service role can delete memories"
    ON public.user_memories
    FOR DELETE
    USING (true);

-- ============================================
-- Step 7: Grant permissions
-- ============================================

GRANT ALL ON public.user_memories TO authenticated;
GRANT ALL ON public.user_memories TO service_role;

-- ============================================
-- Step 8: Add documentation comments
-- ============================================

COMMENT ON TABLE public.user_memories IS
    'MemO: Intelligent semantic memory storage with pgvector for conversation context (Task #42597)';

COMMENT ON COLUMN public.user_memories.embedding IS
    'Sentence embedding vector (384-dim from all-MiniLM-L6-v2)';

COMMENT ON COLUMN public.user_memories.memory_type IS
    'Memory type: context, preference, emotion, or fact';

COMMENT ON COLUMN public.user_memories.importance IS
    'Memory importance score (0.0-1.0) for retrieval ranking';

-- ============================================
-- Step 9: Create helper function for semantic search
-- ============================================

CREATE OR REPLACE FUNCTION search_user_memories(
    p_user_id TEXT,
    p_query_embedding vector(384),
    p_similarity_threshold FLOAT DEFAULT 0.7,
    p_limit INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    user_id TEXT,
    session_id UUID,
    memory_text TEXT,
    memory_type TEXT,
    importance FLOAT,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    similarity_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        um.id,
        um.user_id,
        um.session_id,
        um.memory_text,
        um.memory_type,
        um.importance,
        um.metadata,
        um.created_at,
        1 - (um.embedding <=> p_query_embedding) AS similarity_score
    FROM public.user_memories um
    WHERE um.user_id = p_user_id
        AND um.embedding IS NOT NULL
        AND 1 - (um.embedding <=> p_query_embedding) >= p_similarity_threshold
    ORDER BY um.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Step 10: Create monitoring view
-- ============================================

CREATE OR REPLACE VIEW public.user_memory_stats AS
SELECT
    user_id,
    COUNT(*) as total_memories,
    COUNT(DISTINCT session_id) as total_sessions,
    COUNT(DISTINCT memory_type) as memory_types_used,
    AVG(importance) as avg_importance,
    MAX(created_at) as last_memory_at,
    MIN(created_at) as first_memory_at
FROM public.user_memories
GROUP BY user_id;

GRANT SELECT ON public.user_memory_stats TO authenticated;
GRANT SELECT ON public.user_memory_stats TO service_role;

-- ============================================
-- Verification queries (run these to confirm success)
-- ============================================

-- Check that table was created
SELECT 'user_memories table exists' as status
FROM information_schema.tables
WHERE table_name = 'user_memories' AND table_schema = 'public';

-- Check pgvector extension
SELECT 'pgvector extension enabled' as status
FROM pg_extension WHERE extname = 'vector';

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'user_memories'
ORDER BY indexname;

-- Check RLS is enabled
SELECT 'RLS is ' || CASE WHEN relrowsecurity THEN 'ENABLED' ELSE 'DISABLED' END as status
FROM pg_class
WHERE relname = 'user_memories';

-- ============================================
-- DONE! ✅
-- ============================================
-- Next steps:
-- 1. Verify SUPABASE_KEY in .env is your service_role key (not anon key)
-- 2. Restart your backend: docker-compose restart
-- 3. Test with: python test_memo_storage.py
-- ============================================
