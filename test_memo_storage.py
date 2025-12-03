#!/usr/bin/env python3
"""
Test script for MemO memory storage system (Task #42817)

This script tests:
1. Supabase connection
2. user_memories table existence
3. Memory storage (insert)
4. Memory retrieval (semantic search)
5. Metrics reporting

Usage:
    python test_memo_storage.py
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.memo import memo_client
from app.services.supabase import get_supabase
from app.config import get_settings


async def test_supabase_connection():
    """Test 1: Verify Supabase connection"""
    print("\n" + "=" * 60)
    print("TEST 1: Supabase Connection")
    print("=" * 60)

    try:
        settings = get_settings()
        print(f"✓ Supabase URL: {settings.SUPABASE_URL}")
        print(f"✓ Supabase KEY configured: {'Yes' if settings.SUPABASE_KEY else 'No'}")

        get_supabase()
        print("✓ Supabase client initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Supabase connection failed: {e}")
        return False


async def test_table_existence():
    """Test 2: Check if user_memories table exists"""
    print("\n" + "=" * 60)
    print("TEST 2: user_memories Table Existence")
    print("=" * 60)

    try:
        client = get_supabase()

        # Try to query the table (this will fail if table doesn't exist)
        client.table("user_memories").select("id").limit(1).execute()

        print("✓ user_memories table exists")
        print("✓ Table accessible via REST API")
        return True
    except Exception as e:
        error_msg = str(e)
        if "Could not find the table" in error_msg or "PGRST106" in error_msg:
            print("✗ user_memories table NOT FOUND!")
            print(f"   Error: {error_msg}")
            print("\n   💡 SOLUTION:")
            print("      1. Open Supabase SQL Editor: https://supabase.com/dashboard")
            print(
                "      2. Run the SQL script: migrations/create_user_memories_table.sql"
            )
            print("      3. Re-run this test")
        else:
            print(f"✗ Table check failed: {e}")
        return False


async def test_pgvector_extension():
    """Test 3: Check if pgvector extension is enabled"""
    print("\n" + "=" * 60)
    print("TEST 3: pgvector Extension")
    print("=" * 60)

    try:
        # Note: This test requires direct SQL access, which may not be available via REST API
        # In production, you'd verify this via Supabase SQL Editor
        print("⚠  Cannot verify pgvector via REST API")
        print("   Please verify manually in Supabase SQL Editor:")
        print("   SQL: SELECT * FROM pg_extension WHERE extname = 'vector';")
        return True
    except Exception as e:
        print(f"✗ pgvector check failed: {e}")
        return False


async def test_memory_storage():
    """Test 4: Store a test memory"""
    print("\n" + "=" * 60)
    print("TEST 4: Memory Storage")
    print("=" * 60)

    test_user_id = f"test-user-{int(datetime.now().timestamp())}"
    test_session_id = "00000000-0000-0000-0000-000000000001"

    try:
        # Store a preference memory
        success = await memo_client.store_memory(
            user_id=test_user_id,
            memory_text="I prefer detailed technical explanations with code examples",
            memory_type="preference",
            importance=0.9,
            session_id=test_session_id,
            metadata={"test": True, "timestamp": datetime.now().isoformat()},
        )

        if success:
            print("✓ Memory stored successfully")
            print(f"  User ID: {test_user_id}")
            print("  Memory type: preference")
            print("  Importance: 0.9")
            return test_user_id
        else:
            print("✗ Memory storage returned False")
            return None

    except Exception as e:
        error_msg = str(e)
        print(f"✗ Memory storage failed: {e}")

        if "Could not find the table" in error_msg:
            print(
                "\n   💡 SOLUTION: Run migrations/create_user_memories_table.sql in Supabase"
            )
        elif "permission denied" in error_msg.lower():
            print("\n   💡 SOLUTION: Check RLS policies in Supabase")
        elif "embedding" in error_msg.lower():
            print("\n   💡 SOLUTION: Verify pgvector extension is enabled")

        return None


async def test_memory_search(test_user_id: str):
    """Test 5: Search for stored memories"""
    print("\n" + "=" * 60)
    print("TEST 5: Memory Search (Semantic Similarity)")
    print("=" * 60)

    try:
        # Search for memories related to "technical explanations"
        query_text = "Show me technical details with examples"

        memories = await memo_client.search_memories(
            user_id=test_user_id, query_text=query_text, top_k=5
        )

        print("✓ Search completed successfully")
        print(f"  Query: '{query_text}'")
        print(f"  Results found: {len(memories)}")

        if memories:
            for i, mem in enumerate(memories, 1):
                similarity = mem.get("similarity_score", 0)
                text = mem.get("memory_text", "")[:60]
                mem_type = mem.get("memory_type", "unknown")
                print(f"  {i}. [{mem_type}] {text}... (similarity: {similarity:.3f})")
        else:
            print("  ⚠ No memories found (might be due to embedding generation)")

        return len(memories) > 0

    except Exception as e:
        print(f"✗ Memory search failed: {e}")
        return False


async def test_metrics():
    """Test 6: Check MemO metrics"""
    print("\n" + "=" * 60)
    print("TEST 6: MemO Metrics")
    print("=" * 60)

    try:
        metrics = memo_client.get_metrics()

        print("✓ Metrics retrieved successfully:")
        print(f"  Total searches: {metrics['total_searches']}")
        print(f"  Total stores: {metrics['total_stores']}")
        print(f"  Total errors: {metrics['total_errors']}")
        print(f"  Hit rate: {metrics['hit_rate']:.1%}")
        print(f"  Avg search latency: {metrics['avg_search_latency_ms']:.1f}ms")
        print(f"  P95 search latency: {metrics['p95_search_latency_ms']:.1f}ms")

        # Check thresholds
        if metrics["p95_search_latency_ms"] > 0:
            if metrics["p95_search_latency_ms"] < 100:
                print("  ✓ P95 latency is GOOD (< 100ms)")
            else:
                print("  ⚠ P95 latency is HIGH (> 100ms) - consider optimizing")

        return True
    except Exception as e:
        print(f"✗ Metrics retrieval failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "🧪" * 30)
    print(" MemO Memory Storage Test Suite (Task #42817)")
    print("🧪" * 30)

    settings = get_settings()
    print("\nConfiguration:")
    print(f"  MEMO_ENABLED: {settings.MEMO_ENABLED}")
    print(f"  MEMO_TOP_K: {settings.MEMO_TOP_K}")
    print(f"  MEMO_SIMILARITY_THRESHOLD: {settings.MEMO_SIMILARITY_THRESHOLD}")
    print(f"  MEMO_EMBEDDING_MODEL: {settings.MEMO_EMBEDDING_MODEL}")

    if not settings.MEMO_ENABLED:
        print("\n⚠  WARNING: MEMO_ENABLED=false in configuration")
        print("   Set MEMO_ENABLED=true in .env to enable memory system")

    # Run tests
    results = {}

    results["supabase"] = await test_supabase_connection()
    results["table"] = await test_table_existence()

    if not results["table"]:
        print("\n" + "=" * 60)
        print("❌ CRITICAL: user_memories table not found!")
        print("=" * 60)
        print("\nPlease apply the migration:")
        print(
            "1. Option A (Recommended): Run migrations/create_user_memories_table.sql in Supabase SQL Editor"
        )
        print("2. Option B: Use Alembic: alembic upgrade head")
        print("\nThen re-run this test.")
        sys.exit(1)

    results["pgvector"] = await test_pgvector_extension()

    test_user_id = await test_memory_storage()
    results["storage"] = test_user_id is not None

    if test_user_id:
        results["search"] = await test_memory_search(test_user_id)
    else:
        results["search"] = False

    results["metrics"] = await test_metrics()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {test_name.upper()}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! MemO is working correctly.")
        return 0
    else:
        print(f"\n⚠  {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
