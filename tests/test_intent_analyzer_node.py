import app.langgraph_nodes as nodes
from app.langgraph_nodes import EmotionData, IntentAnalyzer, MODE_EMOTIONAL_SUPPORT
from app.routing.models import CurrentMode, Intent, IntentResult, UtilityPath


def _base_state(transcript: str = "Please summarize this.") -> dict:
    return {
        "session_id": "test-session",
        "audio_bytes": b"",
        "transcript": transcript,
        "user_emotion": EmotionData(label="neutral", confidence=0.6),
        "intent": "",
        "current_mode": "",
        "utility_path": None,
        "router_path": "",
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


def test_intent_analyzer_sets_router_and_mode(monkeypatch):
    analyzer = IntentAnalyzer()

    fake_result = IntentResult(
        intent=Intent.UTILITY,
        current_mode=CurrentMode.UTILITY_DIRECT,
        utility_path=UtilityPath.DIRECT,
        confidence=0.93,
        reasoning="stubbed",
    )

    async def fake_router(user_message: str, session_id: str, tier0_result=None, prosody=None):
        assert session_id == "test-session"
        return fake_result

    monkeypatch.setattr(nodes, "classify_intent_and_mode", fake_router)

    state = _base_state("How do I reset my password?")
    updated = analyzer(state)

    assert updated["intent"] == Intent.UTILITY.value
    assert updated["current_mode"] == CurrentMode.UTILITY_DIRECT.value
    assert updated["utility_path"] == UtilityPath.DIRECT.value
    assert updated["router_path"] == "direct"


def test_intent_analyzer_falls_back_on_error(monkeypatch):
    analyzer = IntentAnalyzer()

    async def raise_router(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(nodes, "classify_intent_and_mode", raise_router)

    state = _base_state("Need help please")
    updated = analyzer(state)

    assert updated["intent"] == Intent.EMOTIONAL_SUPPORT.value
    assert updated["current_mode"] == MODE_EMOTIONAL_SUPPORT
    assert updated["utility_path"] is None
    assert updated["router_path"] == "emotional"
