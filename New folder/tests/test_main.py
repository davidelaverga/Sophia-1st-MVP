import io
import time
from unittest.mock import patch

from fastapi.testclient import TestClient

import main as app_module

client = TestClient(app_module.app)


def auth():
    return {"Authorization": "Bearer test-key"}


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


@patch("app.services.mistral.transcribe_audio_with_voxtral", return_value="What is APY?")
@patch("app.services.mistral.generate_llm_reply", return_value="APY stands for annual percentage yield")
@patch("app.services.tts.synthesize_inworld", return_value=b"ID3mock-mp3")
@patch("app.services.supabase.upload_audio_and_get_url", return_value="https://example.com/resp.mp3")
@patch("app.services.supabase.insert_emotion_score")
@patch("app.services.supabase.insert_conversation_session")
@patch("app.services.emotion.analyze_emotion_text", side_effect=[app_module.Emotion(label="neutral", confidence=0.83), app_module.Emotion(label="positive", confidence=0.78)])
def test_chat(mock_em, mock_session, mock_ins, mock_up, mock_tts, mock_gen, mock_tr):
    wav_bytes = b"RIFF....WAVEfmt "
    files = {"file": ("u.wav", io.BytesIO(wav_bytes), "audio/wav")}
    r = client.post("/chat", headers=auth(), files=files)
    assert r.status_code == 200
    data = r.json()
    assert set(["transcript","reply","user_emotion","sophia_emotion","audio_url"]).issubset(data.keys())


def test_missing_auth():
    r = client.get("/")  # public endpoint OK
    files = {"file": ("u.wav", io.BytesIO(b"RIFF"), "audio/wav")}
    r2 = client.post("/transcribe", files=files)
    assert r2.status_code == 401
