-- SQL script to create a test user in the Supabase database
-- This will ensure we have a valid user_id for foreign key constraints

-- Direct insert with ON CONFLICT DO NOTHING to avoid errors if email already exists
INSERT INTO users (id, email, created_at, updated_at)
VALUES 
    ('00000000-0000-0000-0000-000000000000', 'test@example.com', NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- If the above fails due to UUID conflict, try with a different UUID
-- Uncomment and run this if the first insert fails
-- INSERT INTO users (id, email, created_at, updated_at)
-- VALUES 
--     ('11111111-1111-1111-1111-111111111111', 'test2@example.com', NOW(), NOW())
-- ON CONFLICT (email) DO NOTHING;
