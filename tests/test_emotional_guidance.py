import json
from pathlib import Path


from app.services import emotional_guidance as eg


def test_static_store_loads_yaml_and_defaults_to_neutral(tmp_path: Path):
    yaml_file = tmp_path / "guidance.yaml"
    yaml_file.write_text(
        "neutral:\n  - stay calm\njoy:\n  - celebrate\n", encoding="utf-8"
    )
    store = eg._StaticGuidanceStore(yaml_file)
    assert store.get("joy") == ["celebrate"]
    # Unknown emotion falls back to neutral
    assert store.get("unknown") == ["stay calm"]


def test_emotional_guidance_service_success(monkeypatch):
    # Fake HTTP POST returning a guidance list
    def fake_post(url, payload, timeout):
        return {"guidance": [f"hello {payload['emotion']}"]}

    provider = eg.EmotionalGuidanceProvider(
        mode="service", service_url="http://example", http_post=fake_post
    )
    guidance = provider.get_guidance("sad")
    assert guidance == ["hello sad"]


def test_emotional_guidance_service_failure_falls_back(monkeypatch, tmp_path: Path):
    yaml_file = tmp_path / "guidance.yaml"
    yaml_file.write_text("neutral:\n  - fallback\n", encoding="utf-8")

    def failing_post(url, payload, timeout):
        raise RuntimeError("boom")

    provider = eg.EmotionalGuidanceProvider(
        mode="service",
        service_url="http://example",
        http_post=failing_post,
        yaml_path=yaml_file,
    )
    guidance = provider.get_guidance("happy")
    assert guidance == ["fallback"]


def test_default_http_post_handles_json_response(monkeypatch):
    # Build a tiny HTTP handler that returns a JSON body
    class FakeResponse:
        def __init__(self, body: bytes):
            self.status = 200
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        return FakeResponse(json.dumps({"guidance": ["ok"]}).encode("utf-8"))

    monkeypatch.setattr(eg.urllib.request, "urlopen", fake_urlopen)
    provider = eg.EmotionalGuidanceProvider(service_url="http://example")
    body = provider._default_http_post("http://example", {"emotion": "neutral"}, 0.1)
    assert body["guidance"] == ["ok"]


def test_format_guidance_block_and_prompt():
    block = eg.format_guidance_block(["one", "two"])
    assert "Emotion guidance cues" in block
    prompt = eg.build_emotion_guided_prompt(
        message="Hi", emotion_label="joy", emotion_confidence=0.9, guidance=["tip"]
    )
    assert "The user seems joy" in prompt
    assert "tip" in prompt
