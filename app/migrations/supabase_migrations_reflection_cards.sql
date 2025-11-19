-- Migration: Create reflection_cards table
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.reflection_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    title TEXT,
    summary TEXT NOT NULL,
    insight_tags TEXT[] DEFAULT '{}',
    sophia_emotion JSONB,
    user_emotion JSONB,
    shared BOOLEAN DEFAULT FALSE,
    discord_message_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_reflection_cards_user_id ON public.reflection_cards(user_id);
CREATE INDEX IF NOT EXISTS idx_reflection_cards_conversation_id ON public.reflection_cards(conversation_id);
CREATE INDEX IF NOT EXISTS idx_reflection_cards_created_at ON public.reflection_cards(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reflection_cards_shared ON public.reflection_cards(shared) WHERE shared = TRUE;

-- Enable Row Level Security (optional)
ALTER TABLE public.reflection_cards ENABLE ROW LEVEL SECURITY;

-- Create policy to allow authenticated users to read their own reflections
CREATE POLICY "Users can view own reflections"
ON public.reflection_cards
FOR SELECT
USING (true); -- For now, allow all reads (API key protected at FastAPI level)

-- Create policy to allow service role to insert/update
CREATE POLICY "Service role can insert reflections"
ON public.reflection_cards
FOR INSERT
WITH CHECK (true); -- API handles auth

CREATE POLICY "Service role can update reflections"
ON public.reflection_cards
FOR UPDATE
USING (true);

-- Grant permissions to service role
GRANT ALL ON public.reflection_cards TO service_role;
GRANT SELECT ON public.reflection_cards TO anon;

-- Add comment for documentation
COMMENT ON TABLE public.reflection_cards IS 'Stores reflection cards generated from meaningful conversation moments';