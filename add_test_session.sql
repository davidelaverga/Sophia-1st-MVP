-- SQL script to add test conversation session
-- Run this AFTER adding the test user

-- Add the test conversation session with the fixed ID used in the application
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

-- Verify the session was created
SELECT * FROM conversation_sessions WHERE id = '00000000-1111-2222-3333-444444444444';
