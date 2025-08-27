-- SQL script to create the users table in the Supabase database
-- This table is required for foreign key constraints in emotion_scores and conversation_sessions

-- Create users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create a default test user
INSERT INTO users (id, email, created_at, updated_at)
VALUES 
    ('00000000-0000-0000-0000-000000000000', 'test@example.com', NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- Grant necessary permissions (adjust as needed for your Supabase setup)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policy for authenticated users
CREATE POLICY "Users are viewable by authenticated users"
    ON users FOR SELECT
    TO authenticated
    USING (true);

-- Create policy for service role to manage users
CREATE POLICY "Service role can manage users"
    ON users FOR ALL
    TO service_role
    USING (true);
