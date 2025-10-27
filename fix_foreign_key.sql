-- SQL script to fix the foreign key constraint issue
-- This script will identify and fix the schema mismatch between users and conversation_sessions

-- First, let's check which schema the conversation_sessions.user_id foreign key is pointing to
SELECT
    tc.constraint_name,
    tc.table_schema AS table_schema,
    tc.table_name AS table_name,
    kcu.column_name AS column_name,
    ccu.table_schema AS foreign_schema_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM
    information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name='conversation_sessions';

-- Now let's add the user to the correct schema based on the foreign key reference
-- Option 1: If foreign key points to auth.users
INSERT INTO auth.users (id, email, created_at, updated_at)
VALUES 
    ('00000000-0000-0000-0000-000000000000', 'test@example.com', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Option 2: If foreign key points to public.users (which seems to be the case based on your export)
INSERT INTO public.users (id, email, created_at, updated_at)
VALUES 
    ('00000000-0000-0000-0000-000000000000', 'test@example.com', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Let's also check if there are any RLS policies that might be preventing the insert
SELECT * FROM pg_policies WHERE tablename = 'conversation_sessions';

-- Now try to insert the conversation session again
INSERT INTO conversation_sessions (
    id, 
    transcript, 
    reply, 
    user_emotion_label, 
    user_emotion_confidence, 
    sophia_emotion_label, 
    sophia_emotion_confidence, 
    audio_url, 
    user_id,
    created_at,
    updated_at
)
VALUES (
    '00000000-1111-2222-3333-444444444444',
    'Test transcript',
    'Test reply',
    'neutral',
    0.5,
    'neutral',
    0.5,
    'https://example.com/audio.mp3',
    '00000000-0000-0000-0000-000000000000',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;
