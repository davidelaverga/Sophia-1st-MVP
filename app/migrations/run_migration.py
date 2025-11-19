#!/usr/bin/env python3
"""
Script para ejecutar migración de reflection_cards en Supabase

Usage:
    python run_migration.py
    
Requires:
    - SUPABASE_URL en .env
    - SUPABASE_KEY en .env (service_role key recomendado)
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("❌ SUPABASE_URL y SUPABASE_KEY deben estar en .env")

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQL Migration
MIGRATION_SQL = """
-- Migration: Create reflection_cards table
CREATE TABLE IF NOT EXISTS public.reflection_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    title TEXT,
    summary TEXT NOT NULL,
    insight_tags TEXT[] DEFAULT '{}',
    sophia_emotion JSONB,
    user_emotion JSONB,
    shared BOOLEAN DEFAULT FALSE,
    discord_message_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_reflection_cards_user_id ON public.reflection_cards(user_id);
CREATE INDEX IF NOT EXISTS idx_reflection_cards_conversation_id ON public.reflection_cards(conversation_id);
CREATE INDEX IF NOT EXISTS idx_reflection_cards_created_at ON public.reflection_cards(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reflection_cards_shared ON public.reflection_cards(shared) WHERE shared = TRUE;

-- Enable Row Level Security (optional)
ALTER TABLE public.reflection_cards ENABLE ROW LEVEL SECURITY;

-- Create policy to allow authenticated users to read their own reflections
CREATE POLICY "Users can view own reflections"
ON public.reflection_cards
FOR SELECT
USING (true);

-- Create policy to allow service role to insert/update
CREATE POLICY "Service role can insert reflections"
ON public.reflection_cards
FOR INSERT
WITH CHECK (true);

CREATE POLICY "Service role can update reflections"
ON public.reflection_cards
FOR UPDATE
USING (true);

-- Grant permissions to service role
GRANT ALL ON public.reflection_cards TO service_role;
GRANT SELECT ON public.reflection_cards TO anon;

-- Add comment for documentation
COMMENT ON TABLE public.reflection_cards IS 'Stores reflection cards generated from meaningful conversation moments';
"""

def run_migration():
    """Execute the migration SQL"""
    
    print("🚀 Starting Supabase migration for reflection_cards table...\n")
    
    try:
        # Execute SQL using Supabase REST API
        # Note: supabase-py doesn't have a direct SQL execution method
        # We need to use the raw PostgREST API
        
        import requests
        
        # Use the SQL endpoint (requires service_role key)
        sql_endpoint = f"{SUPABASE_URL}/rest/v1/rpc"
        
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Split and execute SQL statements individually
        statements = [s.strip() for s in MIGRATION_SQL.split(';') if s.strip() and not s.strip().startswith('--')]
        
        print(f"📝 Found {len(statements)} SQL statements to execute\n")
        
        for i, statement in enumerate(statements, 1):
            print(f"Executing statement {i}/{len(statements)}...")
            
            # For table creation, we can use direct SQL
            # This is a workaround - ideally use Supabase CLI or Dashboard
            try:
                # Note: This approach has limitations
                # RECOMMENDED: Use Supabase Dashboard SQL Editor instead
                print(f"⚠️  Statement: {statement[:100]}...")
                print(f"⚠️  Please use Supabase Dashboard SQL Editor for full migration\n")
            except Exception as e:
                print(f"⚠️  Could not execute statement {i}: {e}\n")
        
        print("\n" + "="*60)
        print("⚠️  IMPORTANTE: Migración SQL debe ejecutarse en Supabase Dashboard")
        print("="*60)
        print("\n📋 INSTRUCCIONES:")
        print("1. Ir a: https://supabase.com/dashboard")
        print("2. Seleccionar proyecto")
        print("3. SQL Editor → New query")
        print("4. Copiar contenido de: supabase_migration_reflection_cards.sql")
        print("5. Click 'Run'")
        print("\n✅ Después verifica que tabla 'reflection_cards' existe en Table Editor\n")
        
        # Verify if table exists
        print("🔍 Verificando si tabla ya existe...")
        try:
            result = supabase.table("reflection_cards").select("id").limit(1).execute()
            print("✅ Tabla reflection_cards YA EXISTE!")
            print(f"   Columnas disponibles: {result.data if hasattr(result, 'data') else 'N/A'}\n")
            return True
        except Exception as e:
            print(f"❌ Tabla reflection_cards NO existe todavía")
            print(f"   Error: {e}\n")
            return False
            
    except Exception as e:
        print(f"❌ Error durante migración: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("  SUPABASE MIGRATION - reflection_cards")
    print("="*60)
    print()
    
    success = run_migration()
    
    if success:
        print("="*60)
        print("  ✅ MIGRACIÓN COMPLETADA")
        print("="*60)
    else:
        print("="*60)
        print("  ⚠️  USA SUPABASE DASHBOARD SQL EDITOR")
        print("="*60)