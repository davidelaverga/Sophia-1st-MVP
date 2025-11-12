import pytest

try:
    from app.services.emotion import Emotion, infer_text_emotion
except ModuleNotFoundError as exc:
    if exc.name == "pydantic":
        pytest.skip(
            "pydantic is required for text emotion tests", allow_module_level=True
        )
    raise

try:
    from app.langgraph_nodes import SophiaLangGraph
except ModuleNotFoundError as exc:
    if exc.name in {"langgraph", "langchain"}:
        SophiaLangGraph = None
    else:
        raise


def test_infer_text_emotion_uses_text_analyzer(monkeypatch):
    def fake_analyzer(message: str):
        assert message == "Feeling optimistic about staking."
        return Emotion(label="positive", confidence=0.91)

    monkeypatch.setattr(
        "app.services.emotion.analyze_emotion_text", fake_analyzer, raising=False
    )

    result = infer_text_emotion("Feeling optimistic about staking.")

    assert result.label == "positive"
    assert result.confidence == 0.91


def test_infer_text_emotion_falls_back_for_empty(monkeypatch):
    def _should_not_run(*_args, **_kwargs):
        raise AssertionError("Analyzer should not be called for blank text")

    monkeypatch.setattr(
        "app.services.emotion.analyze_emotion_text",
        _should_not_run,
        raising=False,
    )

    result = infer_text_emotion("   ")

    assert result.label == "neutral"
    assert result.confidence == 0.7


def test_infer_text_emotion_heuristic_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.services.emotion.analyze_emotion_text",
        lambda *_args, **_kwargs: Emotion(label="neutral", confidence=0.5),
        raising=False,
    )

    result = infer_text_emotion("I'm really worried about this launch")

    assert result.label == "anxious"
    assert result.confidence > 0.7


@pytest.mark.skipif(SophiaLangGraph is None, reason="LangGraph not installed")
def test_process_text_conversation_applies_detected_emotion(monkeypatch):
    detected = Emotion(label="sad", confidence=0.88)

    def fake_infer(message: str) -> Emotion:
        assert message == "Need some reassurance"
        return detected

    monkeypatch.setattr(
        "app.langgraph_nodes.infer_text_emotion", fake_infer, raising=False
    )

    class FakeCompiledGraph:
        def invoke(self, state):
            state["llm_response"] = "Here is a reply."
            state["audio_url"] = ""
            state["sophia_emotion"] = state["user_emotion"]
            return state

    class FakeStateGraph:
        def __init__(self, *_args, **_kwargs):
            pass

        def add_node(self, *_args, **_kwargs):
            return None

        def add_edge(self, *_args, **_kwargs):
            return None

        def compile(self):
            return FakeCompiledGraph()

    monkeypatch.setattr("app.langgraph_nodes.StateGraph", FakeStateGraph, raising=False)

    graph = SophiaLangGraph()
    result_state = graph.process_text_conversation(
        message="Need some reassurance", session_id="sess-text"
    )

    assert result_state["user_emotion"].label == "sad"
    assert result_state["user_emotion"].confidence == 0.88
