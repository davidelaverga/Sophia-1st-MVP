import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.emotional_guidance import build_emotion_guided_prompt


def test_build_text_stream_prompt_includes_guidance():
    prompt = build_emotion_guided_prompt(
        "Walk me through staking yields.",
        "anxious",
        0.82,
        ["Acknowledge concerns", "Offer clear reassurance"],
    )

    assert "anxious" in prompt
    assert "0.82" in prompt
    assert "Emotion guidance cues" in prompt
    assert "Acknowledge concerns" in prompt
    assert "User question: Walk me through staking yields." in prompt


def test_build_text_stream_prompt_handles_empty_message():
    prompt = build_emotion_guided_prompt("", "", None, [])

    assert "(no text provided)" in prompt
    # Default label should fall back to neutral wording
    assert "neutral" in prompt


def test_build_text_stream_prompt_includes_conversation_context():
    context_block = (
        "Recent topics: staking\nRecent conversation:\nUser: Hi\nSophia: Hello!"
    )
    prompt = build_emotion_guided_prompt(
        "What's next?",
        "calm",
        0.5,
        [],
        conversation_context=context_block,
    )

    assert "Conversation context" in prompt
    assert "Sophia: Hello!" in prompt
