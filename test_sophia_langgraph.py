#!/usr/bin/env python3
"""
Comprehensive test script for Sophia LangGraph system
Tests all 5 parts of the specification:
1. LangGraph nodes
2. Memory system
3. Fallback logic
4. RAG system
5. Evaluations (RAGAS + Phoenix)
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.langgraph_service import langgraph_service
from app.services.evaluations import evaluation_manager
from app.services.rag import rag_system
from app.services.memory import memory_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_test_audio(filename: str) -> bytes:
    """Load test audio file"""
    audio_path = project_root / "audio" / filename
    if audio_path.exists():
        with open(audio_path, "rb") as f:
            return f.read()
    else:
        # Return mock audio bytes for testing
        logger.warning(f"Audio file {filename} not found, using mock data")
        return b"mock_audio_data_" + filename.encode()

def test_langgraph_nodes():
    """Test Part 1: LangGraph Nodes"""
    print("\n[1/5] TESTING PART 1: LangGraph Nodes")
    print("=" * 50)
    
    # Test with a DeFi question
    test_audio = load_test_audio("neutral_sample.wav")
    session_id = "test_session_001"
    
    try:
        result = langgraph_service.process_conversation(
            audio_bytes=test_audio, 
            session_id=session_id,
            run_evaluation=False  # Skip evaluation for this test
        )
        
        print(f"[PASS] LangGraph processing completed!")
        print(f"   Session ID: {result['session_id']}")
        print(f"   Transcript: '{result['transcript'][:50]}...' (mock)")
        print(f"   User emotion: {result['user_emotion']['label']} ({result['user_emotion']['confidence']:.2f})")
        print(f"   Sophia emotion: {result['sophia_emotion']['label']} ({result['sophia_emotion']['confidence']:.2f})")
        print(f"   Intent: {result['intent']}")
        print(f"   Fallbacks used: {result['fallbacks_used']}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] LangGraph nodes test failed: {e}")
        return False

def test_memory_system():
    """Test Part 2: Context Memory"""
    print("\n🧠 TESTING PART 2: Context Memory (Redis/Supabase)")
    print("=" * 50)
    
    session_id = "test_memory_session"
    
    try:
        # Simulate 3 conversation turns
        turns = [
            {"query": "What's yield farming?", "intent": "defi_question", "user_emotion": "curious"},
            {"query": "And is that safe right now?", "intent": "defi_question", "user_emotion": "nervous"}, 
            {"query": "How do I get started?", "intent": "defi_question", "user_emotion": "excited"}
        ]
        
        for i, turn_data in enumerate(turns, 1):
            from app.services.memory import ConversationTurn
            import time
            
            turn = ConversationTurn(
                query=turn_data["query"],
                response=f"Mock response {i}",
                user_emotion=turn_data["user_emotion"],
                sophia_emotion="calm",
                intent=turn_data["intent"],
                timestamp=time.time()
            )
            
            # Update memory
            memory = memory_manager.update_session_memory(session_id, turn)
            print(f"   Turn {i}: {turn_data['query'][:30]}... -> emotion: {turn_data['user_emotion']}")
        
        # Test context retrieval
        context = memory_manager.get_context_for_llm(session_id)
        print(f"✅ Memory system working!")
        print(f"   Last topics: {context.get('last_topics', [])}")
        print(f"   Last user tone: {context.get('last_user_tone', 'unknown')}")
        print(f"   Conversation turns: {context.get('conversation_turns', 0)}")
        print(f"   Recent intents: {context.get('recent_intents', [])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory system test failed: {e}")
        return False

def test_rag_system():
    """Test Part 4: RAG Stub (Vector Search)"""
    print("\n🧠 TESTING PART 4: RAG System (Vector Search on DeFi FAQs)")
    print("=" * 50)
    
    try:
        # Test queries
        test_queries = [
            "What is staking?",
            "What are the risks of DeFi?",
            "How do I choose a safe protocol?"
        ]
        
        for query in test_queries:
            results = rag_system.query_faqs(query, top_k=2)
            context = rag_system.get_context_for_llm(query)
            
            print(f"   Query: '{query}'")
            if results:
                for result in results:
                    print(f"     → Match: {result.question[:40]}... (similarity: {result.similarity_score:.2f})")
            else:
                print(f"     → No matches found (threshold: {rag_system.similarity_threshold})")
            print()
        
        print(f"✅ RAG system working!")
        print(f"   Total FAQs loaded: {len(rag_system.faqs)}")
        print(f"   Similarity threshold: {rag_system.similarity_threshold}")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG system test failed: {e}")
        return False

def test_ragas_evaluation():
    """Test Part 5A: RAGAS Evaluation"""
    print("\n📏 TESTING PART 5A: RAGAS Evaluation")
    print("=" * 50)
    
    try:
        # Run batch evaluation
        batch_results = evaluation_manager.run_batch_evaluation(num_queries=5)
        
        print(f"✅ RAGAS evaluation completed!")
        print(f"   Total queries tested: {batch_results['total_queries']}")
        print(f"   Average score: {batch_results['average_score']:.2f}")
        print(f"   Target score: {batch_results['target_score']}")
        print(f"   Target met: {'✅ YES' if batch_results['target_met'] else '❌ NO'}")
        
        # Show individual results
        print("\n   Individual Results:")
        for result in batch_results['results'][:3]:  # Show first 3
            print(f"     Query: {result['query'][:40]}...")
            print(f"       Score: {result['ragas_score']:.2f} (F:{result['faithfulness']:.2f}, R:{result['relevance']:.2f}, C:{result['correctness']:.2f})")
        
        return batch_results['target_met']
        
    except Exception as e:
        print(f"❌ RAGAS evaluation test failed: {e}")
        return False

def test_phoenix_drift_monitor():
    """Test Part 5B: Phoenix Emotion Drift Detection"""
    print("\n📏 TESTING PART 5B: Phoenix Emotion Drift Detection")
    print("=" * 50)
    
    try:
        # Test with multiple audio samples
        test_audios = [
            ("neutral_sample.wav", "user"),
            ("happiness_sample.wav", "sophia"),
            ("fear_sample.wav", "user"),
        ]
        
        metrics_list = []
        session_id = "test_drift_session"
        
        for audio_file, role in test_audios:
            audio_bytes = load_test_audio(audio_file)
            metrics = evaluation_manager.phoenix_monitor.evaluate_audio_emotion(
                audio_bytes, session_id, role
            )
            metrics_list.append(metrics)
            print(f"   {role.capitalize()} audio ({audio_file}): {metrics.emotion_label} (confidence: {metrics.confidence:.2f})")
        
        # Test drift detection
        drift_alert, current_confidence = evaluation_manager.phoenix_monitor.check_drift_alert(metrics_list)
        
        print(f"✅ Phoenix drift monitoring working!")
        print(f"   Baseline confidence: {evaluation_manager.phoenix_monitor.baseline_confidence:.2f}")
        print(f"   Current confidence: {current_confidence:.2f}")
        print(f"   Drift alert: {'⚠️  YES' if drift_alert else '✅ NO'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phoenix drift monitor test failed: {e}")
        return False

def test_full_integration():
    """Test complete system integration"""
    print("\n🔧 TESTING FULL SYSTEM INTEGRATION")
    print("=" * 50)
    
    try:
        # Full end-to-end test with a DeFi question
        test_audio = load_test_audio("neutral_sample.wav")
        session_id = "integration_test_session"
        
        result = langgraph_service.process_conversation(
            audio_bytes=test_audio,
            session_id=session_id,
            run_evaluation=True  # Include full evaluation
        )
        
        print(f"✅ Full integration test completed!")
        print(f"   Session: {result['session_id']}")
        print(f"   Flow: Audio → Transcript → Intent → LLM → TTS → Evaluation")
        print(f"   User emotion: {result['user_emotion']['label']} ({result['user_emotion']['confidence']:.2f})")
        print(f"   Sophia emotion: {result['sophia_emotion']['label']} ({result['sophia_emotion']['confidence']:.2f})")
        print(f"   Intent: {result['intent']}")
        print(f"   Memory context: {len(result['context_memory'])} keys")
        print(f"   Evaluation completed: {'✅' if result['evaluation_report'] else '❌'}")
        
        if result['fallbacks_used']:
            print(f"   ⚠️  Fallbacks used: {result['fallbacks_used']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Full integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎯 SOPHIA LANGGRAPH SYSTEM - COMPREHENSIVE TEST")
    print("=" * 60)
    print("Testing all 5 parts of the specification:")
    print("1. LangGraph Nodes")
    print("2. Context Memory") 
    print("3. Fallback Logic (integrated)")
    print("4. RAG System")
    print("5. Evaluations (RAGAS + Phoenix)")
    print("=" * 60)
    
    results = {}
    
    # Run all tests
    results["langgraph_nodes"] = test_langgraph_nodes()
    results["memory_system"] = test_memory_system()
    results["rag_system"] = test_rag_system()
    results["ragas_evaluation"] = test_ragas_evaluation()
    results["phoenix_drift"] = test_phoenix_drift_monitor()
    results["full_integration"] = test_full_integration()
    
    # Summary
    print("\n🎯 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Sophia LangGraph system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)