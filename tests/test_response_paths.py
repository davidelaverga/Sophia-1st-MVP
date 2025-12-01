"""Unit tests for DIRECT, LIGHT, and AGENTIC response paths."""

from unittest.mock import AsyncMock, patch

from app.langgraph_nodes import EmotionData, ResponseGenerator, ResponsePath


def _base_state():
    return {
        "session_id": "unit-test-session",
        "audio_bytes": b"",
        "transcript": "",
        "user_emotion": EmotionData(label="neutral", confidence=0.6),
        "intent": "",
        "context_memory": {},
        "memo_context": {"memories": []},
        "llm_response": "",
        "response_path": "",
        "sophia_emotion": EmotionData(label="neutral", confidence=0.0),
        "audio_url": "",
        "tts_bytes": b"",
        "evaluation_logs": [],
        "emotion_guidance": [],
        "fallback_used": {},
        "use_voxtral": False,
        "supabase_token": None,
        "cancel_check": None,
    }


def test_direct_path_returns_snippet_without_llm():
    state = _base_state()
    state["transcript"] = "hi"
    state["user_emotion"] = EmotionData(label="joy", confidence=0.9)
    generator = ResponseGenerator(use_voxtral=False)
    generator._response_path_split = True

    with (
        patch("app.langgraph_nodes.generate_llm_reply") as mock_llm,
        patch("app.langgraph_nodes.memory_manager.get_context_for_llm") as mock_flash,
        patch("app.langgraph_nodes.trigger_phoenix_bg") as mock_phoenix,
    ):
        generator._process_with_legacy_llm(state)

    assert state["response_path"] == ResponsePath.DIRECT.value
    mock_llm.assert_not_called()
    mock_flash.assert_not_called()
    mock_phoenix.assert_called_once_with(
        state["session_id"], state["transcript"], False
    )
    assert (
        state["llm_response"]
        == "Hi—I'm here with you. What would you like to talk about?"
    )


def test_direct_path_negative_emotion_uses_calming_message():
    state = _base_state()
    state["transcript"] = "привет"
    state["user_emotion"] = EmotionData(label="panic", confidence=0.9)
    generator = ResponseGenerator(use_voxtral=False)
    generator._response_path_split = True

    with patch("app.langgraph_nodes.trigger_phoenix_bg"):
        generator._process_with_legacy_llm(state)

    assert state["response_path"] == ResponsePath.DIRECT.value
    assert state["llm_response"] == "I'm here. We can take this one step at a time."


def test_light_path_uses_tone_and_token_limit():
    state = _base_state()
    state["transcript"] = "Need a quick reset, I'm feeling a bit low."
    state["intent"] = "emotional_support"
    state["user_emotion"] = EmotionData(label="sad", confidence=0.8)
    generator = ResponseGenerator(use_voxtral=False)
    generator._response_path_split = True

    with (
        patch(
            "app.langgraph_nodes.memory_manager.get_context_for_llm", return_value={}
        ) as mock_flash,
        patch(
            "app.langgraph_nodes.memo_client.get_context_for_llm",
            new_callable=AsyncMock,
        ) as mock_memo,
        patch(
            "app.langgraph_nodes.generate_llm_reply", return_value="light reply"
        ) as mock_llm,
        patch("app.langgraph_nodes.trigger_phoenix_bg") as mock_phoenix,
    ):
        generator._process_with_legacy_llm(state)

    assert state["response_path"] == ResponsePath.LIGHT.value
    mock_flash.assert_called_once()
    mock_memo.assert_not_called()
    _, kwargs = mock_llm.call_args
    assert kwargs["max_tokens"] == 180
    assert "gentle" in kwargs["system_prompt"].lower()
    mock_phoenix.assert_called_once_with(
        state["session_id"], state["transcript"], False
    )


def test_agentic_path_includes_emotion_guidance_in_prompt():
    state = _base_state()
    state["transcript"] = "Explain APY versus APR for staking."
    state["intent"] = "defi_question"
    generator = ResponseGenerator(use_voxtral=False)
    generator._response_path_split = True

    with (
        patch(
            "app.langgraph_nodes.memory_manager.get_context_for_llm",
            return_value={
                "last_topics": ["staking"],
                "conversation_turns": 2,
                "recent_turns": [
                    {"user": "Hi Sophia", "sophia": "Hey there"},
                    {"user": "Explain APY versus APR for staking.", "sophia": ""},
                ],
            },
        ) as mock_flash,
        patch(
            "app.langgraph_nodes.memo_client.get_context_for_llm",
            new=AsyncMock(
                return_value={
                    "memories": [
                        {
                            "text": "Enjoys analogies",
                            "type": "preference",
                            "relevance": 0.82,
                        }
                    ]
                }
            ),
        ) as mock_memo,
        patch(
            "app.langgraph_nodes.get_emotional_guidance",
            return_value=["Be encouraging"],
        ) as mock_guidance,
        patch(
            "app.langgraph_nodes.rag_system.get_context_for_llm",
            return_value="APY reflects compound interest over a year.",
        ) as mock_rag,
        patch(
            "app.langgraph_nodes.prompt_composer.compose_system_prompt",
            return_value="system-with-guidance",
        ) as mock_prompt,
        patch(
            "app.langgraph_nodes.generate_llm_reply", return_value="agentic reply"
        ) as mock_llm,
    ):
        generator._process_with_legacy_llm(state)

    assert state["response_path"] == ResponsePath.AGENTIC.value
    mock_flash.assert_called_once()
    mock_memo.assert_called_once()
    mock_guidance.assert_called_once()
    # mock_rag.assert_called_once()
    _, prompt_kwargs = mock_prompt.call_args
    assert prompt_kwargs["emotion_guidance"] == ["Be encouraging"]
    assert prompt_kwargs["memory_context"]["memories"]
    args, kwargs = mock_llm.call_args
    assert kwargs["system_prompt"] == "system-with-guidance"
    assert "Explain APY" in args[0]
    assert "Conversation so far" in args[0]
    assert "Hi Sophia" in args[0]


def test_affect_snapshot_seeds_direct_path_emotion():
    state = _base_state()
    state["transcript"] = "hello there"
    state["user_emotion"] = EmotionData(label="neutral", confidence=0.2)
    generator = ResponseGenerator(use_voxtral=False)
    generator._response_path_split = True

    snapshot = {"emotion": "panic", "confidence": 0.92}

    with (
        patch(
            "app.langgraph_nodes.memory_manager.get_context_for_llm", return_value={}
        ),
        patch("app.langgraph_nodes.memory_manager.peek_affect", return_value=snapshot),
        patch("app.langgraph_nodes.trigger_phoenix_bg"),
    ):
        generator._process_with_legacy_llm(state)

    assert state["response_path"] == ResponsePath.DIRECT.value
    assert state["user_emotion"].label == "panic"
    assert state["llm_response"] == "I'm here. We can take this one step at a time."


def test_mode_direct_greeting_uses_template_and_skips_memory():
    state = _base_state()
    state["transcript"] = "hi sophia"
    # Seed some fake memory to ensure DIRECT clears it
    state["memo_context"] = {"memories": ["old"]}
    state["context_memory"] = {"last_topics": ["yesterday"]}
    generator = ResponseGenerator(use_voxtral=False)

    result_state = generator._process_direct_mode(state)

    greetings = {
        "Hello! How can I help you today?",
        "Hi there! What brings you here?",
        "Hey! Nice to see you!",
        "Hello! I'm here to assist you.",
    }
    assert result_state["llm_response"] in greetings
    assert result_state["memo_context"] == {"memories": []}
    assert result_state["context_memory"] == {}


def test_mode_direct_complex_input_falls_back_to_light():
    state = _base_state()
    state["transcript"] = "Can you remind me what we talked about yesterday?"
    generator = ResponseGenerator(use_voxtral=False)

    with patch.object(
        ResponseGenerator,
        "_process_light_mode",
        return_value=state,
    ) as mock_light:
        result_state = generator._process_direct_mode(state)

    mock_light.assert_called_once_with(state)
    assert result_state is state


def test_mode_direct_pure_ack_uses_ack_template():
    state = _base_state()
    state["transcript"] = "ok"
    generator = ResponseGenerator(use_voxtral=False)

    result_state = generator._process_direct_mode(state)

    assert result_state["llm_response"] == "Got it. I'm right here with you."


def test_mode_direct_prefaced_question_not_treated_as_ack():
    state = _base_state()
    state["transcript"] = "Ok, can you explain staking?"
    generator = ResponseGenerator(use_voxtral=False)

    with patch.object(
        ResponseGenerator,
        "_process_light_mode",
        return_value=state,
    ) as mock_light:
        result_state = generator._process_direct_mode(state)

    mock_light.assert_called_once_with(state)
    assert result_state is state
