import struct

import pytest
from fastapi import HTTPException

from app import audio_utils
from app.helpers import (
    prosody_features,
    extract_audio,
    validate_audio_upload,
    sse_event,
)


def test_wav_header_pcm16_has_riff_and_expected_sizes():
    header = audio_utils.wav_header_pcm16(
        num_samples=5, sample_rate=8000, num_channels=2
    )
    assert header.startswith(b"RIFF")
    # RIFF chunk size is stored at bytes 4-8 (little endian uint32)
    riff_size = struct.unpack("<I", header[4:8])[0]
    assert riff_size == 36 + 5 * 2  # matches implementation
    assert header.endswith(b"data" + struct.pack("<I", 5 * 2))


def test_avg_abs_pcm16_handles_empty_and_values():
    assert audio_utils.avg_abs_pcm16(b"") == 0.0
    samples = struct.pack("<3h", -1000, 1000, 0)
    assert audio_utils.avg_abs_pcm16(samples) == pytest.approx(666.66, rel=0.01)


def test_pcm16_to_wav_wraps_payload():
    pcm = b"\x01\x02\x03\x04"
    wrapped = audio_utils.pcm16_to_wav(pcm, sample_rate=16000, channels=1)
    assert wrapped.startswith(b"RIFF")
    assert wrapped.endswith(pcm)
    # Header should be 44 bytes for minimal PCM16 WAV
    assert len(wrapped) == 44 + len(pcm)


def test_prosody_features_classifies_basic_intensity_levels():
    # Very low amplitude should return low
    assert prosody_features(b"\x00\x00\x00\x00")["intensity"] == "low"
    # Large amplitude sample -> high
    loud_sample = struct.pack("<1h", 30000)
    assert prosody_features(loud_sample)["intensity"] == "high"


class FakeUploadFile:
    def __init__(self, data: bytes, filename: str, content_type: str):
        self._data = data
        self.filename = filename
        self.content_type = content_type

    async def read(self):
        return self._data


@pytest.mark.asyncio
async def test_extract_audio_accepts_known_headers():
    payload = b"RIFF" + b"\x00" * 10
    upload = FakeUploadFile(payload, filename="test.wav", content_type="audio/wav")
    result = await extract_audio(upload)
    assert result == payload


@pytest.mark.asyncio
async def test_extract_audio_rejects_empty_payload():
    upload = FakeUploadFile(b"", filename="empty.wav", content_type="audio/wav")
    with pytest.raises(HTTPException):
        await extract_audio(upload)


def test_validate_audio_upload_checks_extension_and_content_type():
    valid = FakeUploadFile(b"", filename="clip.ogg", content_type="audio/ogg")
    validate_audio_upload(valid)  # should not raise

    bad_type = FakeUploadFile(b"", filename="clip.ogg", content_type="application/json")
    with pytest.raises(HTTPException):
        validate_audio_upload(bad_type)

    bad_extension = FakeUploadFile(b"", filename="clip.txt", content_type="audio/ogg")
    with pytest.raises(HTTPException):
        validate_audio_upload(bad_extension)


def test_sse_event_formats_payloads_as_json():
    msg = sse_event("update", {"foo": "bar"})
    assert msg.startswith("event: update")
    assert "data: " in msg


@pytest.mark.asyncio
async def test_extract_audio_accepts_mpeg_frame_sync():
    # 0xFF followed by high bits set triggers MPEG frame sync branch
    payload = bytes([0xFF, 0xE0, 0x00, 0x00, 0x01])
    upload = FakeUploadFile(payload, filename="clip.mp3", content_type="audio/mp3")
    result = await extract_audio(upload)
    assert result == payload
