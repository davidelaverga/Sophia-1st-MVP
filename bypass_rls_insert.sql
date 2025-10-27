-- SQL script to bypass RLS policies and insert conversation session
-- IMPORTANT: This script must be run with service_role permissions in the SQL Editor

-- Begin transaction
BEGIN;

-- Set role to service_role to bypass RLS policies
SET LOCAL ROLE service_role;

-- Insert the conversation session with the service role
-- This bypasses the RLS policy that requires user_id = auth.uid()
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

-- Also add the session ID from the error logs
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
    '27dae80e-20e8-4314-8c39-31ae7eb6bcb8',
    'Another test transcript',
    'Another test reply',
    'neutral',
    0.5,
    'neutral',
    0.5,
    'https://example.com/audio2.mp3',
    '00000000-0000-0000-0000-000000000000',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Add test emotion scores for the session
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

-- Verify the data was created
SELECT * FROM conversation_sessions WHERE id = '00000000-1111-2222-3333-444444444444';
SELECT * FROM emotion_scores WHERE session_id = '00000000-1111-2222-3333-444444444444';

COMMIT;
