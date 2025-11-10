"""
Tests for Voxtral Large unified audio-to-response pipeline
"""

from unittest.mock import patch
from app.services.voxtral_large import VoxtralLargeService, HybridVoxtralService


class TestVoxtralLargeService:
    """Test suite for VoxtralLargeService"""

    def test_initialization(self):
        """Test that service initializes correctly"""
        with patch("app.services.voxtral_large.get_settings") as mock_settings:
            mock_settings.return_value.MISTRAL_API_KEY = "test_key"

            service = VoxtralLargeService()

            assert service.model == "voxtral-mini-latest"
            assert service.client is not None

    def test_build_context_prompt_basic(self):
        """Test context prompt building without context"""
        with patch("app.services.voxtral_large.get_settings") as mock_settings:
            mock_settings.return_value.MISTRAL_API_KEY = "test_key"

            service = VoxtralLargeService()
            prompt = service._build_context_prompt()

            assert "Sophia" in prompt
            assert "DeFi mentor" in prompt
            assert "50 words" in prompt

    def test_build_context_prompt_with_context(self):
        """Test context prompt building with full context"""
        with patch("app.services.voxtral_large.get_settings") as mock_settings:
            mock_settings.return_value.MISTRAL_API_KEY = "test_key"

            service = VoxtralLargeService()

            context = {
                "last_topics": ["yield farming", "staking"],
                "user_emotion": {"label": "curious", "confidence": 0.85},
                "last_user_tone": "interested",
                "intent": "defi_question",
                "recent_intents": ["defi_question", "small_talk"],
                "rag_context": "Yield farming involves providing liquidity...",
            }

            prompt = service._build_context_prompt(context)

            assert "yield farming" in prompt
            assert "staking" in prompt
            assert "curious" in prompt
            assert "0.85" in prompt
            assert "defi_question" in prompt
            assert "Yield farming" in prompt

    def test_detect_audio_extension(self):
        """Test audio format detection"""
        with patch("app.services.voxtral_large.get_settings") as mock_settings:
            mock_settings.return_value.MISTRAL_API_KEY = "test_key"

            service = VoxtralLargeService()

            # Test WAV
            wav_bytes = b"RIFF" + b"\x00" * 100
            assert service._detect_audio_extension(wav_bytes) == ".wav"

            # Test MP3
            mp3_bytes = b"ID3" + b"\x00" * 100
            assert service._detect_audio_extension(mp3_bytes) == ".mp3"

            # Test OGG
            ogg_bytes = b"OggS" + b"\x00" * 100
            assert service._detect_audio_extension(ogg_bytes) == ".ogg"

            # Test default fallback
            unknown_bytes = b"\x00\x00\x00\x00"
            assert service._detect_audio_extension(unknown_bytes) == ".wav"


class TestHybridVoxtralService:
    """Test suite for HybridVoxtralService with fallback logic"""

    def test_initialization(self):
        """Test that hybrid service initializes with primary service"""
        with patch("app.services.voxtral_large.get_settings") as mock_settings:
            mock_settings.return_value.MISTRAL_API_KEY = "test_key"

            service = HybridVoxtralService()

            assert service.primary is not None
            assert isinstance(service.primary, VoxtralLargeService)

    def test_build_legacy_prompt(self):
        """Test legacy prompt building for fallback"""
        with patch("app.services.voxtral_large.get_settings") as mock_settings:
            mock_settings.return_value.MISTRAL_API_KEY = "test_key"

            service = HybridVoxtralService()

            context = {
                "user_emotion": {"label": "worried", "confidence": 0.75},
                "last_topics": ["impermanent loss"],
                "rag_context": "Impermanent loss occurs when...",
            }

            transcript = "What is impermanent loss?"
            prompt = service._build_legacy_prompt(transcript, context)

            assert "worried" in prompt
            assert "impermanent loss" in prompt
            assert "Impermanent loss occurs" in prompt
            assert transcript in prompt

    @patch("app.services.voxtral_large.VoxtralLargeService.generate_response")
    def test_generate_response_uses_primary(self, mock_generate):
        """Test that hybrid service uses primary by default"""
        with patch("app.services.voxtral_large.get_settings") as mock_settings:
            mock_settings.return_value.MISTRAL_API_KEY = "test_key"

            mock_generate.return_value = "Test response from Voxtral Large"

            service = HybridVoxtralService()
            audio_bytes = b"fake_audio_data"

            result = service.generate_response(audio_bytes)

            assert result["response"] == "Test response from Voxtral Large"
            assert result["service_used"] == "voxtral_large"
            mock_generate.assert_called_once()

    @patch("app.services.voxtral_large.VoxtralLargeService.generate_response")
    def test_generate_response_fallback_on_error(self, mock_generate):
        """Test that hybrid service falls back to legacy on error"""
        with patch("app.services.voxtral_large.get_settings") as mock_settings:
            mock_settings.return_value.MISTRAL_API_KEY = "test_key"

            # Make primary fail
            mock_generate.side_effect = Exception("API rate limited")

            with patch(
                "app.services.mistral.transcribe_audio_with_voxtral"
            ) as mock_stt:
                with patch("app.services.mistral.generate_llm_reply") as mock_llm:
                    mock_stt.return_value = "What is staking?"
                    mock_llm.return_value = "Staking involves locking tokens..."

                    service = HybridVoxtralService()
                    audio_bytes = b"fake_audio_data"

                    result = service.generate_response(audio_bytes)

                    assert result["service_used"] == "legacy_pipeline"
                    assert result["transcript"] == "What is staking?"
                    assert "Staking" in result["response"]

    @patch("app.services.voxtral_large.VoxtralLargeService.stream_response")
    def test_stream_response_uses_primary(self, mock_stream):
        """Test that streaming uses primary by default"""
        with patch("app.services.voxtral_large.get_settings") as mock_settings:
            mock_settings.return_value.MISTRAL_API_KEY = "test_key"

            # Mock streaming response
            mock_stream.return_value = iter(["Token1 ", "Token2 ", "Token3"])

            service = HybridVoxtralService()
            audio_bytes = b"fake_audio_data"

            tokens = list(service.stream_response(audio_bytes))

            assert len(tokens) == 3
            assert all(t["service_used"] == "voxtral_large" for t in tokens)
            assert tokens[0]["token"] == "Token1 "


def test_integration_context_enrichment():
    """Integration test for context enrichment across the pipeline"""
    with patch("app.services.voxtral_large.get_settings") as mock_settings:
        mock_settings.return_value.MISTRAL_API_KEY = "test_key"

        service = VoxtralLargeService()

        # Simulate a conversation with rich context
        context = {
            "last_topics": ["liquidity pools", "yield farming"],
            "user_emotion": {"label": "confused", "confidence": 0.90},
            "last_user_tone": "seeking clarification",
            "intent": "defi_question",
            "recent_intents": ["defi_question", "defi_question", "emotional_support"],
            "rag_context": "Liquidity pools are smart contracts that hold two or more tokens...",
        }

        system_prompt = "You are Sophia, an expert DeFi educator."

        prompt = service._build_context_prompt(context, system_prompt)

        # Verify all context elements are included
        assert "Sophia" in prompt
        assert "liquidity pools" in prompt
        assert "yield farming" in prompt
        assert "confused" in prompt
        assert "0.90" in prompt
        assert "defi_question" in prompt
        assert "seeking clarification" in prompt
        assert "smart contracts" in prompt

        # Verify structure
        parts = prompt.split(" | ")
        assert len(parts) > 1  # Multiple context parts
