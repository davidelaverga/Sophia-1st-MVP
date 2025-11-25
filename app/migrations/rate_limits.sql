-- Rate Limits and Payment Plans Migration
-- Run this in Supabase SQL Editor

-- 1. Add plan_tier to users table (if not exists)
-- Note: Adjust table name if your users table has a different name
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'plan_tier'
    ) THEN
        ALTER TABLE users 
        ADD COLUMN plan_tier VARCHAR(32) NOT NULL DEFAULT 'FREE',
        ADD COLUMN plan_renews_at TIMESTAMPTZ NULL;
        
        -- Create index for faster lookups
        CREATE INDEX idx_users_plan_tier ON users(plan_tier);
    END IF;
END $$;

-- 2. Create user_daily_usage table
CREATE TABLE IF NOT EXISTS user_daily_usage (
    user_id UUID NOT NULL,
    usage_date DATE NOT NULL,
    voice_seconds INTEGER NOT NULL DEFAULT 0,
    text_messages INTEGER NOT NULL DEFAULT 0,
    text_tokens INTEGER NOT NULL DEFAULT 0, -- Optional, for future use
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, usage_date)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_user_daily_usage_user_id 
    ON user_daily_usage(user_id);
    
CREATE INDEX IF NOT EXISTS idx_user_daily_usage_date 
    ON user_daily_usage(usage_date DESC);

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_user_daily_usage_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-updating timestamp
DROP TRIGGER IF EXISTS user_daily_usage_updated_at ON user_daily_usage;
CREATE TRIGGER user_daily_usage_updated_at
    BEFORE UPDATE ON user_daily_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_user_daily_usage_timestamp();

-- 3. Create helper function to upsert daily usage
CREATE OR REPLACE FUNCTION upsert_user_daily_usage(
    p_user_id UUID,
    p_usage_date DATE,
    p_voice_seconds INTEGER DEFAULT 0,
    p_text_messages INTEGER DEFAULT 0,
    p_text_tokens INTEGER DEFAULT 0
)
RETURNS user_daily_usage AS $$
DECLARE
    result user_daily_usage;
BEGIN
    INSERT INTO user_daily_usage (
        user_id, 
        usage_date, 
        voice_seconds, 
        text_messages, 
        text_tokens
    )
    VALUES (
        p_user_id, 
        p_usage_date, 
        p_voice_seconds, 
        p_text_messages, 
        p_text_tokens
    )
    ON CONFLICT (user_id, usage_date) 
    DO UPDATE SET
        voice_seconds = user_daily_usage.voice_seconds + EXCLUDED.voice_seconds,
        text_messages = user_daily_usage.text_messages + EXCLUDED.text_messages,
        text_tokens = user_daily_usage.text_tokens + EXCLUDED.text_tokens,
        updated_at = NOW()
    RETURNING * INTO result;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- 4. Create view for easy usage queries
CREATE OR REPLACE VIEW user_usage_summary AS
SELECT 
    u.user_id,
    u.usage_date,
    u.voice_seconds,
    u.text_messages,
    u.text_tokens,
    u.created_at,
    -- Calculate percentage of limits (assuming FREE tier)
    ROUND((u.voice_seconds::NUMERIC / 600) * 100, 2) as voice_percent_free,
    ROUND((u.text_messages::NUMERIC / 40) * 100, 2) as text_percent_free
FROM user_daily_usage u;

-- 5. Cleanup old usage data (keep last 90 days)
-- Run this periodically as a cron job
CREATE OR REPLACE FUNCTION cleanup_old_usage_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_daily_usage
    WHERE usage_date < CURRENT_DATE - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 6. Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE ON user_daily_usage TO authenticated;
-- GRANT EXECUTE ON FUNCTION upsert_user_daily_usage TO authenticated;

-- 7. Insert test data (optional, for testing)
-- INSERT INTO user_daily_usage (user_id, usage_date, voice_seconds, text_messages)
-- VALUES 
--     ('00000000-0000-0000-0000-000000000000', CURRENT_DATE, 300, 20),
--     ('00000000-0000-0000-0000-000000000000', CURRENT_DATE - 1, 500, 35);

-- Verify tables created
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_name IN ('user_daily_usage', 'users')
ORDER BY table_name;