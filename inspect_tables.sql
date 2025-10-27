-- SQL script to inspect table structure in Supabase

-- Check users table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM 
    information_schema.columns
WHERE 
    table_name = 'users'
ORDER BY 
    ordinal_position;

-- Check conversation_sessions table structure and constraints
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM
    information_schema.table_constraints tc
JOIN
    information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
LEFT JOIN
    information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
WHERE
    tc.table_name = 'conversation_sessions';

-- Check if any users exist
SELECT * FROM users LIMIT 10;
