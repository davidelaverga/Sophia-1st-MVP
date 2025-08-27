-- SQL script to create the users table if it doesn't exist
-- This ensures we have the correct table structure before adding the test user

-- Create the users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policies for the users table
CREATE POLICY "Users are viewable by authenticated users" 
    ON users FOR SELECT 
    TO authenticated 
    USING (true);

CREATE POLICY "Users can be created by authenticated users" 
    ON users FOR INSERT 
    TO authenticated 
    WITH CHECK (true);

CREATE POLICY "Users can be updated by the user themselves" 
    ON users FOR UPDATE 
    TO authenticated 
    USING (auth.uid() = id);

-- Now insert the test user with the exact UUID needed by the application
INSERT INTO users (id, email, created_at, updated_at)
VALUES 
    ('00000000-0000-0000-0000-000000000000', 'test@example.com', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Verify the user was created
SELECT * FROM users WHERE id = '00000000-0000-0000-0000-000000000000';
