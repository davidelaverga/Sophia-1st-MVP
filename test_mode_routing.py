"""Test script for Task #42729: Mode routing verification"""

from app.langgraph_nodes import (
    ModeClassifier,
    EmotionData,
    MODE_DIRECT,
    MODE_LIGHT,
    MODE_UTILITY_AGENTIC,
    MODE_EMOTIONAL_SUPPORT,
)


def test_mode_classifier():
    """Test ModeClassifier logic with various inputs"""
    classifier = ModeClassifier()

    test_cases = [
        # Test DIRECT mode (simple greetings)
        {
            "transcript": "Hello",
            "intent": "small_talk",
            "emotion": "joy",
            "expected": MODE_DIRECT,
            "description": "Simple greeting should use DIRECT mode",
        },
        {
            "transcript": "Hi there",
            "intent": "small_talk",
            "emotion": "neutral",
            "expected": MODE_DIRECT,
            "description": "Short greeting with neutral emotion",
        },
        # Test EMOTIONAL_SUPPORT mode
        {
            "transcript": "I'm feeling very anxious",
            "intent": "emotional_support",
            "emotion": "anxious",
            "expected": MODE_EMOTIONAL_SUPPORT,
            "description": "Anxious emotion should trigger emotional support",
        },
        {
            "transcript": "I'm feeling sad today",
            "intent": "emotional_support",
            "emotion": "sad",
            "expected": MODE_EMOTIONAL_SUPPORT,
            "description": "Sadness should use emotional support mode",
        },
        {
            "transcript": "I feel like ending it all",
            "intent": "crisis",
            "emotion": "panic",
            "expected": MODE_EMOTIONAL_SUPPORT,
            "description": "Crisis intent should use emotional support",
        },
        # Test UTILITY_AGENTIC mode
        {
            "transcript": "Can you explain how DeFi yield farming works compared to traditional staking mechanisms and what are the risks involved?",
            "intent": "defi_question",
            "emotion": "neutral",
            "expected": MODE_UTILITY_AGENTIC,
            "description": "Complex DeFi query should use utility agentic mode",
        },
        {
            "transcript": "Compare the differences between liquidity pools and yield farms",
            "intent": "defi_question",
            "emotion": "neutral",
            "expected": MODE_UTILITY_AGENTIC,
            "description": "Comparison query should use utility agentic mode",
        },
        # Test LIGHT mode (default)
        {
            "transcript": "What is DeFi?",
            "intent": "defi_question",
            "emotion": "neutral",
            "expected": MODE_LIGHT,
            "description": "Simple DeFi question should use light mode",
        },
        {
            "transcript": "How are you doing today?",
            "intent": "small_talk",
            "emotion": "neutral",
            "expected": MODE_LIGHT,
            "description": "Casual question should use light mode",
        },
        {
            "transcript": "Tell me about staking",
            "intent": "defi_question",
            "emotion": "excited",
            "expected": MODE_LIGHT,
            "description": "Short DeFi query should use light mode",
        },
    ]

    print("=" * 80)
    print("TESTING MODE CLASSIFIER (Task #42729)")
    print("=" * 80)

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        state = {
            "session_id": f"test_{i}",
            "transcript": test_case["transcript"],
            "intent": test_case["intent"],
            "user_emotion": EmotionData(label=test_case["emotion"], confidence=0.8),
        }

        result = classifier(state)
        mode = result["current_mode"]

        status = "✅ PASS" if mode == test_case["expected"] else "❌ FAIL"
        if mode == test_case["expected"]:
            passed += 1
        else:
            failed += 1

        print(f"\nTest {i}: {status}")
        print(f"  Description: {test_case['description']}")
        print(f"  Transcript: '{test_case['transcript'][:60]}...'")
        print(f"  Intent: {test_case['intent']}, Emotion: {test_case['emotion']}")
        print(f"  Expected: {test_case['expected']}")
        print(f"  Got: {mode}")

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed}/{len(test_cases)} tests passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = test_mode_classifier()
    exit(0 if success else 1)
