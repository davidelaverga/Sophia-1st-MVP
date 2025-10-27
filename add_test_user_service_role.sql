-- SQL script to add test user using service role (bypasses RLS)
-- IMPORTANT: This script must be run with service_role key permissions in the SQL Editor

-- Since we can see from the RLS policies that only service_role has full permissions,
-- we need to make sure we're using the service role context

-- Begin transaction
BEGIN;

-- Insert directly into public.users table
-- The service_role has a policy allowing ALL operations
INSERT INTO public.users (id, email, created_at, updated_at)
VALUES 
    ('00000000-0000-0000-0000-000000000000', 'test@example.com', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET 
    email = 'test@example.com',
    updated_at = NOW();

-- Verify the user was created
SELECT * FROM public.users WHERE id = '00000000-0000-0000-0000-000000000000';

COMMIT;
