-- SQL script to inspect foreign key relationships
-- This will help us understand where the foreign key is pointing

-- Check foreign key constraints for conversation_sessions table
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_schema AS foreign_schema_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM
    information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name='conversation_sessions';

-- Check if the user exists in auth.users
SELECT * FROM auth.users WHERE id = '00000000-0000-0000-0000-000000000000';

-- Check if the user exists in public.users
SELECT * FROM public.users WHERE id = '00000000-0000-0000-0000-000000000000';

-- Check the schema of the users table that the foreign key is pointing to
SELECT 
    table_schema, 
    table_name 
FROM 
    information_schema.tables 
WHERE 
    table_name = 'users';

-- Check for any RLS policies on the conversation_sessions table
SELECT * FROM pg_policies WHERE tablename = 'conversation_sessions';
