-- SQL script to reset user daily usage to 90% of their plan limits
-- This is useful for testing the usage limit alerts and modal

-- Replace 'USER_ID_HERE' with the actual user ID
-- Example: '4668de84-7222-4900-a0da-d4f319bf9bc2'

-- For FREE plan:
--   daily_voice_seconds: 600 (10 minutes) → 90% = 540 seconds
--   daily_text_messages: 40 → 90% = 36 messages

-- First, check current usage
SELECT 
    user_id,
    usage_date,
    voice_seconds,
    text_messages,
    text_tokens
FROM user_daily_usage
WHERE user_id = '4668de84-7222-4900-a0da-d4f319bf9bc2'
  AND usage_date = CURRENT_DATE;

-- Update to 90% of FREE plan limits
-- Voice: 600 seconds * 0.9 = 540 seconds
-- Text: 40 messages * 0.9 = 36 messages
UPDATE user_daily_usage
SET 
    voice_seconds = 540,
    text_messages = 36,
    text_tokens = 0
WHERE user_id = '4668de84-7222-4900-a0da-d4f319bf9bc2'
  AND usage_date = CURRENT_DATE;

-- If no row exists for today, insert one
INSERT INTO user_daily_usage (user_id, usage_date, voice_seconds, text_messages, text_tokens)
VALUES (
    '4668de84-7222-4900-a0da-d4f319bf9bc2',
    CURRENT_DATE,
    540,  -- 90% of 600 seconds
    36,   -- 90% of 40 messages
    0
)
ON CONFLICT (user_id, usage_date) DO UPDATE
SET 
    voice_seconds = 540,
    text_messages = 36,
    text_tokens = 0;

-- Verify the update
SELECT 
    user_id,
    usage_date,
    voice_seconds,
    text_messages,
    ROUND((voice_seconds / 600.0) * 100, 2) as voice_percent,
    ROUND((text_messages / 40.0) * 100, 2) as text_percent
FROM user_daily_usage
WHERE user_id = '4668de84-7222-4900-a0da-d4f319bf9bc2'
  AND usage_date = CURRENT_DATE;




