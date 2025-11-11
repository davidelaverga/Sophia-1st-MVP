import sys
import types

_fake_dotenv = types.ModuleType("dotenv")
_fake_dotenv.load_dotenv = lambda *args, **kwargs: None
_fake_dotenv.find_dotenv = lambda *args, **kwargs: ""
sys.modules.setdefault("dotenv", _fake_dotenv)

from app.services.emotional_guidance import (  # noqa: E402
    EmotionalGuidanceProvider,
    format_guidance_block,
)


def test_yaml_guidance_covers_all_supported_emotions():
    provider = EmotionalGuidanceProvider(mode="static")
    emotions = [
        "neutral",
        "joy",
        "sad",
        "anxious",
        "angry",
        "fearful",
        "grief",
        "panic",
        "excited",
    ]
    for emotion in emotions:
        guidance = provider.get_guidance(emotion)
        assert guidance, f"No guidance returned for {emotion}"


def test_service_mode_uses_remote_guidance():
    captured = {}

    def fake_post(url, payload, timeout):
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {"guidance": ["remote tip"]}

    provider = EmotionalGuidanceProvider(
        mode="service",
        service_url="https://example.test/guidance",
        timeout_seconds=1.0,
        http_post=fake_post,
    )

    guidance = provider.get_guidance("joy")

    assert guidance == ["remote tip"]
    assert captured["payload"] == {"emotion": "joy"}


def test_service_failure_falls_back_to_yaml():
    called = {"value": False}

    def failing_post(url, payload, timeout):
        called["value"] = True
        raise RuntimeError("network down")

    provider = EmotionalGuidanceProvider(
        mode="service",
        service_url="https://example.test/guidance",
        http_post=failing_post,
    )

    guidance = provider.get_guidance("sad")

    assert guidance, "Fallback guidance should not be empty"
    assert called["value"], "Remote service should be attempted before fallback"


def test_format_guidance_block_outputs_bullets():
    block = format_guidance_block(
        ["Validate feelings", "", "Offer next step", "  "]
    )
    assert block.startswith("Emotion guidance cues:")
    assert "- Validate feelings" in block
    assert block.count("\n- ") == 2


def test_format_guidance_block_empty_input():
    block = format_guidance_block([])
    assert block == ""
