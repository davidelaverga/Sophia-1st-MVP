-- Fix Storage RLS Policy for Audio Uploads (Task #42817)
-- Date: 2025-11-25
--
-- PROBLEM:
-- Audio uploads were failing with "403 Unauthorized - new row violates row-level security policy"
-- Root cause: Backend uses SUPABASE_KEY (anon role), not SUPABASE_SERVICE_KEY (service_role)
--
-- SOLUTION:
-- Create RLS policy for 'anon' and 'authenticated' roles (not 'service_role')
-- to allow uploads to the 'audio' bucket

-- Drop existing incorrect policy
DROP POLICY IF EXISTS "service_role_audio_all" ON storage.objects;

-- Create policy for anon and authenticated roles
CREATE POLICY "anon_authenticated_audio_all"
ON storage.objects
FOR ALL
TO anon, authenticated
USING (bucket_id = 'audio')
WITH CHECK (bucket_id = 'audio');

-- Verification query
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'storage'
    AND tablename = 'objects'
    AND policyname = 'anon_authenticated_audio_all';

-- Expected result:
-- schemaname | tablename |         policyname          | permissive |        roles        | cmd
-- -----------+-----------+-----------------------------+------------+--------------------+-----
-- storage    | objects   | anon_authenticated_audio_all| PERMISSIVE | {anon,authenticated}| ALL
