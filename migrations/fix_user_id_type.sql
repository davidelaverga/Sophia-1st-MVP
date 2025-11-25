-- Quick fix: Change user_id from UUID to TEXT in user_memories table
-- Task #42817: Fix Mem0 database schema error
-- Execute this in Supabase SQL Editor: https://supabase.com/dashboard

-- Step 1: Drop the old table (it's empty or has wrong data anyway)
DROP TABLE IF EXISTS public.user_memories CASCADE;

-- Step 2: Recreate with correct schema (user_id as TEXT)
CREATE TABLE public.user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,  -- ✅ Changed from UUID to TEXT
    session_id UUID,
    memory_text TEXT NOT NULL,
    embedding vector(384),  -- ✅ pgvector type for embeddings
    memory_type TEXT DEFAULT 'context',
    importance FLOAT DEFAULT 0.5,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_importance CHECK (importance >= 0.0 AND importance <= 1.0),
    CONSTRAINT valid_memory_type CHECK (memory_type IN ('context', 'preference', 'emotion', 'fact'))
);

-- Step 3: Create indexes
CREATE INDEX idx_user_memories_user_id ON public.user_memories(user_id);
CREATE INDEX idx_user_memories_session_id ON public.user_memories(session_id);
CREATE INDEX idx_user_memories_created_at ON public.user_memories(created_at DESC);
CREATE INDEX idx_user_memories_memory_type ON public.user_memories(memory_type);

-- Step 4: Create vector index for semantic search
CREATE INDEX idx_user_memories_embedding_ivfflat
    ON public.user_memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Step 5: Create trigger for updated_at
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

-- Step 6: Enable RLS and create policies
ALTER TABLE public.user_memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own memories"
    ON public.user_memories FOR SELECT
    USING (true);

CREATE POLICY "Service role can insert memories"
    ON public.user_memories FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Service role can update memories"
    ON public.user_memories FOR UPDATE
    USING (true);

CREATE POLICY "Service role can delete memories"
    ON public.user_memories FOR DELETE
    USING (true);

-- Step 7: Grant permissions
GRANT ALL ON public.user_memories TO authenticated;
GRANT ALL ON public.user_memories TO service_role;

-- Verification query
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'user_memories'
    AND table_schema = 'public'
    AND column_name = 'user_id';

-- Should return: user_id | text | NO
