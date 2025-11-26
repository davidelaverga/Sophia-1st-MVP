#!/usr/bin/env python3
"""Simple test to check if user_memories table exists in Supabase"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.supabase import get_supabase
from app.config import get_settings

def main():
    print("=" * 60)
    print("Quick Supabase user_memories Table Check")
    print("=" * 60)

    settings = get_settings()
    print(f"\nSupabase URL: {settings.SUPABASE_URL}")
    print(f"Supabase KEY configured: {'Yes' if settings.SUPABASE_KEY else 'No'}")

    try:
        client = get_supabase()
        print("✓ Supabase client initialized\n")

        # Try to query user_memories table
        print("Checking user_memories table...")
        result = client.table("user_memories").select("id").limit(1).execute()

        print("✅ SUCCESS! user_memories table EXISTS and is accessible")
        print(f"   Query returned: {len(result.data)} row(s)")

        return 0

    except Exception as e:
        error_msg = str(e)

        if "Could not find the table" in error_msg or "PGRST106" in error_msg:
            print("❌ FAIL! user_memories table NOT FOUND")
            print(f"   Error: {error_msg}\n")
            print("=" * 60)
            print("SOLUTION:")
            print("=" * 60)
            print("Run this SQL in Supabase SQL Editor:")
            print("  migrations/create_user_memories_table.sql")
            print("\nOr visit:")
            print("  https://supabase.com/dashboard/project/[YOUR-PROJECT]/sql")
            print("=" * 60)
            return 1
        else:
            print(f"❌ FAIL! Unexpected error: {e}")
            return 1

if __name__ == "__main__":
    sys.exit(main())
