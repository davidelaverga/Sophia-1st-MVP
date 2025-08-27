-- SQL script to create a test conversation session in the Supabase database
-- This will ensure we have a valid session_id for foreign key constraints in emotion_scores

-- Insert the specific session ID from the error message
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
    '27dae80e-20e8-4314-8c39-31ae7eb6bcb8',  -- The session ID from the error message
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

-- Insert a generic test conversation session with a fixed ID
-- This can be used for testing emotion scores
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
    '00000000-1111-2222-3333-444444444444',  -- Fixed test session ID
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

-- Insert test emotion scores for the test session
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
