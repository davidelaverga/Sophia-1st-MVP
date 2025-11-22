-- Update reflection_cards table for multi-turn support
-- Run this in Supabase SQL Editor

-- Add new fields for enhanced reflections
DO $$ 
BEGIN
    -- Add key_moments if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'reflection_cards' AND column_name = 'key_moments'
    ) THEN
        ALTER TABLE reflection_cards 
        ADD COLUMN key_moments JSONB DEFAULT '[]'::jsonb;
    END IF;
    
    -- Add emotional_arc if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'reflection_cards' AND column_name = 'emotional_arc'
    ) THEN
        ALTER TABLE reflection_cards 
        ADD COLUMN emotional_arc TEXT DEFAULT '';
    END IF;
    
    -- Add message_count if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'reflection_cards' AND column_name = 'message_count'
    ) THEN
        ALTER TABLE reflection_cards 
        ADD COLUMN message_count INTEGER DEFAULT 2;
    END IF;
END $$;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_reflection_cards_message_count 
    ON reflection_cards(message_count);

-- Verify new columns
SELECT 
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'reflection_cards'
    AND column_name IN ('key_moments', 'emotional_arc', 'message_count')
ORDER BY column_name;