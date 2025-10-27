-- Comprehensive SQL script to set up all test data in Supabase
-- IMPORTANT: This script must be run with service_role key permissions in the SQL Editor

-- Begin transaction
BEGIN;

-- STEP 1: Create or ensure the test user exists
-- The service_role has a policy allowing ALL operations on users
INSERT INTO public.users (id, email, created_at, updated_at)
VALUES 
    ('00000000-0000-0000-0000-000000000000', 'test@example.com', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET 
    email = 'test@example.com',
    updated_at = NOW();

-- STEP 2: Create the test conversation session
-- This uses the user_id from step 1
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
    '00000000-1111-2222-3333-444444444444',  -- Fixed test session ID used in the application
    'Test transcript',
    'Test reply',
    'neutral',
    0.5,
    'neutral',
    0.5,
    'https://example.com/audio.mp3',
    '00000000-0000-0000-0000-000000000000',  -- Test user ID
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    transcript = 'Test transcript',
    reply = 'Test reply',
    updated_at = NOW();

-- STEP 3: Add test emotion scores for the session
-- These reference both the user_id and session_id
INSERT INTO emotion_scores (
    session_id,
    role,
    label,
    confidence,
    user_id,
    created_at,
    updated_at
)
VALUES 
    ('00000000-1111-2222-3333-444444444444', 'user', 'neutral', 0.5, '00000000-0000-0000-0000-000000000000', NOW(), NOW()),
    ('00000000-1111-2222-3333-444444444444', 'sophia', 'positive', 0.7, '00000000-0000-0000-0000-000000000000', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- STEP 4: Add the specific session ID from the error message (if needed)
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
    '27dae80e-20e8-4314-8c39-31ae7eb6bcb8',  -- Session ID from error message
    'Another test transcript',
    'Another test reply',
    'neutral',
    0.5,
    'neutral',
    0.5,
    'https://example.com/audio2.mp3',
    '00000000-0000-0000-0000-000000000000',  -- Test user ID
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Verify the data was created
SELECT * FROM public.users WHERE id = '00000000-0000-0000-0000-000000000000';
SELECT * FROM conversation_sessions WHERE id = '00000000-1111-2222-3333-444444444444';
SELECT * FROM emotion_scores WHERE session_id = '00000000-1111-2222-3333-444444444444';

COMMIT;
