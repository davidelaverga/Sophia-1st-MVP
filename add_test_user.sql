-- SQL script to add the test user with the exact UUID needed
-- This will ensure the foreign key constraints can be satisfied

-- First, check if a user with this email already exists and delete it if needed
-- This ensures we can insert our user with the specific UUID
DELETE FROM users WHERE email = 'test@example.com';

-- Now insert the test user with the exact UUID needed by the application
-- The primary key column is named 'id' in the users table
INSERT INTO users (id, email, created_at, updated_at)
VALUES 
    ('00000000-0000-0000-0000-000000000000', 'test@example.com', NOW(), NOW());

-- Verify the user was created
SELECT * FROM users WHERE id = '00000000-0000-0000-0000-000000000000';
