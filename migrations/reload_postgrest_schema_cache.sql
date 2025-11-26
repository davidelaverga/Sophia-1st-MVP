-- Reload PostgREST Schema Cache (Task #42817)
-- Date: 2025-11-25
--
-- PROBLEM:
-- PostgREST caches the database schema for performance. After migrations that change
-- column types (e.g., user_id from UUID to TEXT in user_memories table), the cache
-- becomes stale and causes validation errors like:
-- "invalid input syntax for type uuid" even though the column is actually TEXT.
--
-- SOLUTION:
-- Send a NOTIFY signal to PostgREST to reload its schema cache immediately.
-- This ensures the API layer uses the current database schema.
--
-- WHEN TO USE:
-- Run this after ANY migration that:
-- 1. Changes column types
-- 2. Adds/removes columns
-- 3. Creates/drops tables
-- 4. Modifies constraints
--
-- This is especially important for Supabase hosted databases where PostgREST
-- is the API layer between your app and PostgreSQL.

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';

-- Verification: Check that the schema is up-to-date
-- Run this query to see when PostgREST last reloaded:
-- (This is informational only, not a verification query)
SELECT
    'Schema cache reload signal sent' as status,
    NOW() as executed_at;

-- ============================================
-- DONE! ✅
-- ============================================
-- PostgREST will reload its schema cache within a few seconds.
-- Your application should now see the updated schema.
-- ============================================
