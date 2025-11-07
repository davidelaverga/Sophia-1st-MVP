"""Unit tests covering legacy chat endpoints and pipeline error handling."""

import os
import io
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_DEFAULT_USER_ID", "11111111-1111-1111-1111-111111111111")

from fastapi.testclient import TestClient

import main as app_module
import app.deps as deps_module

TEST_ISS = "https://example.supabase.co/auth/v1"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY_PEM = _PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


class _StubJWKClient:
    def get_signing_key_from_jwt(self, token: str):
        return SimpleNamespace(key=_PUBLIC_KEY_PEM, algorithm="RS256")


def _stub_get_jwk_client(issuer: str):
    return _StubJWKClient()


deps_module._get_jwk_client = _stub_get_jwk_client

client = TestClient(app_module.app)


def _encode_token(payload: dict | None = None) -> str:
    body = {"sub": "user-123", "iss": TEST_ISS}
    if payload:
        body.update(payload)
    return jwt.encode(body, _PRIVATE_KEY, algorithm="RS256", headers={"kid": "test-key"})


def auth(include_discord: bool = False, discord_id: str = "user-123"):
    headers = {"Authorization": f"Bearer {_encode_token()}"}
    if include_discord:
        headers["X-Discord-Id"] = discord_id
    return headers


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json().get("message")


@patch("app.services.mistral.transcribe_audio_with_voxtral", return_value="What is APY?")
@patch("app.services.emotion.analyze_emotion_text")
@patch("app.services.supabase.insert_emotion_score")
def test_transcribe_success(mock_ins, mock_emotion, mock_transcribe):
    mock_emotion.return_value = app_module.Emotion(label="neutral", confidence=0.81)
    wav_bytes = b"RIFF....WAVEfmt "  # fake wav
    files = {"file": ("sample.wav", io.BytesIO(wav_bytes), "audio/wav")}
    r = client.post("/transcribe", headers=auth(), files=files)
    assert r.status_code == 200
    data = r.json()
    assert "text" in data and data["text"] == "What is APY?"
    assert "emotion" in data and data["emotion"]["label"] in {"neutral","positive","negative","unknown"}


def test_transcribe_wrong_type():
    files = {"file": ("notwav.mp3", io.BytesIO(b"xxx"), "audio/mpeg")}
    r = client.post("/transcribe", headers=auth(), files=files)
    assert r.status_code == 400


@patch("app.services.mistral.generate_llm_reply", return_value="APY is annual percentage yield")
def test_generate_response(mock_gen):
    r = client.post("/generate-response", headers=auth(), json={"text": "Explain APY"})
    assert r.status_code == 200
    assert "reply" in r.json()


@patch("app.services.tts.synthesize_inworld", return_value=b"ID3mock-mp3")
@patch("app.services.supabase.upload_audio_and_get_url", return_value="https://example.com/audio.mp3")
@patch("app.services.supabase.insert_emotion_score")
@patch("app.services.emotion.analyze_emotion_text", return_value=app_module.Emotion(label="positive", confidence=0.77))
def test_synthesize(mock_em, mock_ins, mock_up, mock_tts):
    r = client.post("/synthesize", headers=auth(), json={"text": "Hello there"})
    assert r.status_code == 200
    data = r.json()
    assert data["audio_url"].startswith("http")
    assert data["emotion"]["label"] in {"neutral","positive","negative"}


@patch("app.deps.has_user_consent", return_value=True)
@patch("app.services.mistral.transcribe_audio_with_voxtral", return_value="What is APY?")
@patch("app.services.mistral.generate_llm_reply", return_value="APY stands for annual percentage yield")
@patch("app.services.tts.synthesize_inworld", return_value=b"ID3mock-mp3")
@patch("app.services.supabase.upload_audio_and_get_url", return_value="https://example.com/resp.mp3")
@patch("app.services.supabase.insert_emotion_score")
@patch("app.services.supabase.insert_conversation_session")
@patch("app.services.emotion.analyze_emotion_text", side_effect=[app_module.Emotion(label="neutral", confidence=0.83), app_module.Emotion(label="positive", confidence=0.78)])
def test_chat(mock_em, mock_session, mock_ins, mock_up, mock_tts, mock_gen, mock_tr, mock_consent):
    wav_bytes = b"RIFF....WAVEfmt "
    files = {"file": ("u.wav", io.BytesIO(wav_bytes), "audio/wav")}
    r = client.post("/chat", headers=auth(include_discord=True), files=files)
    assert r.status_code == 200
    data = r.json()
    assert set(["transcript","reply","user_emotion","sophia_emotion","audio_url"]).issubset(data.keys())


def test_chat_missing_consent_header_returns_403():
    wav_bytes = b"RIFF....WAVEfmt "
    files = {"file": ("u.wav", io.BytesIO(wav_bytes), "audio/wav")}
    r = client.post("/chat", headers=auth(), files=files)
    assert r.status_code == 403


@patch("app.deps.has_user_consent", return_value=False)
def test_chat_consent_denied_returns_403(mock_consent):
    wav_bytes = b"RIFF....WAVEfmt "
    files = {"file": ("u.wav", io.BytesIO(wav_bytes), "audio/wav")}
    r = client.post("/chat", headers=auth(include_discord=True), files=files)
    assert r.status_code == 403


def test_defi_chat_requires_consent_header():
    wav_bytes = b"RIFF....WAVEfmt "
    files = {"file": ("u.wav", io.BytesIO(wav_bytes), "audio/wav")}
    r = client.post("/defi-chat", headers=auth(), files=files)
    assert r.status_code == 403


@patch("app.deps.has_user_consent", return_value=False)
def test_defi_chat_consent_denied(mock_consent):
    wav_bytes = b"RIFF....WAVEfmt "
    files = {"file": ("u.wav", io.BytesIO(wav_bytes), "audio/wav")}
    r = client.post("/defi-chat", headers=auth(include_discord=True), files=files)
    assert r.status_code == 403


@patch("app.deps.has_user_consent", return_value=True)
@patch("app.services.langgraph_service.langgraph_service.process_conversation")
@patch("app.services.supabase.insert_conversation_session")
@patch("app.services.supabase.insert_emotion_score")
def test_defi_chat_consent_allows_flow(mock_ins_emotion, mock_ins_session, mock_process, mock_consent):
    mock_process.return_value = {
        "session_id": "sess-123",
        "transcript": "What is staking?",
        "reply": "Staking locks tokens to secure the network.",
        "user_emotion": {"label": "neutral", "confidence": 0.7},
        "sophia_emotion": {"label": "positive", "confidence": 0.8},
        "audio_url": "https://example.com/audio.mp3",
        "intent": "defi_question",
        "context_memory": {},
        "fallbacks_used": {},
        "evaluation_logs": [],
        "evaluation_report": None,
    }
    wav_bytes = b"RIFF....WAVEfmt "
    files = {"file": ("u.wav", io.BytesIO(wav_bytes), "audio/wav")}
    r = client.post("/defi-chat", headers=auth(include_discord=True), files=files)
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "sess-123"
    assert data["user_emotion"]["label"] == "neutral"


def test_text_chat_requires_consent_header():
    r = client.post("/text-chat", headers=auth(), json={"message": "Hello"})
    assert r.status_code == 403


@patch("app.deps.has_user_consent", return_value=True)
@patch("app.services.langgraph_service.langgraph_service.process_text_conversation")
@patch("app.services.supabase.insert_conversation_session")
@patch("app.services.supabase.insert_emotion_score")
def test_text_chat_consent_allows_flow(mock_ins_emotion, mock_ins_session, mock_process, mock_consent):
    mock_process.return_value = {
        "session_id": "sess-text",
        "transcript": "Tell me about DeFi",
        "reply": "DeFi enables permissionless finance.",
        "user_emotion": {"label": "neutral", "confidence": 0.75},
        "sophia_emotion": {"label": "neutral", "confidence": 0.6},
        "audio_url": "https://example.com/audio.mp3",
        "intent": "defi_question",
        "context_memory": {},
        "fallbacks_used": {},
        "evaluation_logs": [],
        "evaluation_report": None,
    }
    r = client.post("/text-chat", headers=auth(include_discord=True), json={"message": "Hello"})
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "sess-text"


def test_missing_auth():
    r = client.get("/")  # public endpoint OK
    files = {"file": ("u.wav", io.BytesIO(b"RIFF"), "audio/wav")}
    r2 = client.post("/transcribe", files=files)
    assert r2.status_code == 401
