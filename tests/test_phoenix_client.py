"""
Tests for PhoenixClient emotion classification wrapper.

Task #42841
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from app.emotion.phoenix_client import (
    PhoenixClient,
    PhoenixConfig,
    PhoenixResult,
)


@pytest.fixture
def phoenix_config():
    """Create test PhoenixConfig."""
    return PhoenixConfig(
        base_url="https://api.openai.com/v1",
        api_key="test-api-key",
        timeout_seconds=5.0
    )


@pytest.fixture
def phoenix_client(phoenix_config):
    """Create test PhoenixClient instance."""
    return PhoenixClient(phoenix_config)


class TestPhoenixConfig:
    """Test PhoenixConfig dataclass."""

    def test_config_creation(self):
        """Test creating PhoenixConfig with all fields."""
        config = PhoenixConfig(
            base_url="https://api.openai.com/v1",
            api_key="sk-test123",
            timeout_seconds=10.0
        )
        assert config.base_url == "https://api.openai.com/v1"
        assert config.api_key == "sk-test123"
        assert config.timeout_seconds == 10.0

    def test_config_default_timeout(self):
        """Test PhoenixConfig default timeout value."""
        config = PhoenixConfig(
            base_url="https://api.openai.com/v1",
            api_key="sk-test123"
        )
        assert config.timeout_seconds == 12.0


class TestPhoenixResult:
    """Test PhoenixResult dataclass."""

    def test_result_creation(self):
        """Test creating PhoenixResult."""
        result = PhoenixResult(
            label="anxious",
            confidence=0.85,
            safety_flag=False,
            raw={"test": "data"}
        )
        assert result.label == "anxious"
        assert result.confidence == 0.85
        assert result.safety_flag is False
        assert result.raw == {"test": "data"}


class TestPhoenixClient:
    """Test PhoenixClient functionality."""

    def test_client_initialization(self, phoenix_client, phoenix_config):
        """Test client initialization."""
        assert phoenix_client.config == phoenix_config
        assert phoenix_client.client is not None
        assert phoenix_client.prompt_template is not None

    def test_valid_emotions(self, phoenix_client):
        """Test valid emotion labels are defined."""
        expected_emotions = {
            "joy", "excited", "sad", "anxious", "grief", "panic",
            "anger", "fearful", "calm", "neutral", "hopeful", "lonely"
        }
        assert phoenix_client.VALID_EMOTIONS == expected_emotions

    def test_neutral_fallback(self, phoenix_client):
        """Test neutral fallback result."""
        fallback = phoenix_client.NEUTRAL_FALLBACK
        assert fallback.label == "neutral"
        assert fallback.confidence == 0.3
        assert fallback.safety_flag is False
        assert "fallback" in fallback.raw

    @pytest.mark.asyncio
    async def test_classify_empty_text(self, phoenix_client):
        """Test classify returns neutral for empty text."""
        result = await phoenix_client.classify("")
        assert result.label == "neutral"
        assert result.confidence == 0.3

    @pytest.mark.asyncio
    async def test_classify_success(self, phoenix_client):
        """Test successful emotion classification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "label": "anxious",
                        "confidence": 0.85,
                        "safety_flag": False
                    })
                }
            }]
        }

        with patch.object(phoenix_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await phoenix_client.classify(
                text="I'm really worried about the exam tomorrow",
                prosody_context="pitch: high, pace: fast"
            )

            assert result.label == "anxious"
            assert result.confidence == 0.85
            assert result.safety_flag is False
            assert "choices" in result.raw

    @pytest.mark.asyncio
    async def test_classify_with_prosody(self, phoenix_client):
        """Test classification with prosody context."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "label": "excited",
                        "confidence": 0.92,
                        "safety_flag": False
                    })
                }
            }]
        }

        with patch.object(phoenix_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await phoenix_client.classify(
                text="I got the job!",
                prosody_context="pitch: very high, energy: high, pace: fast"
            )

            # Verify prosody was included in payload
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            user_message = payload['messages'][1]['content']
            assert "additional_context" in user_message
            assert "pitch: very high" in user_message

            assert result.label == "excited"
            assert result.confidence == 0.92

    @pytest.mark.asyncio
    async def test_classify_safety_flag_true(self, phoenix_client):
        """Test classification with safety flag set."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "label": "grief",
                        "confidence": 0.88,
                        "safety_flag": True
                    })
                }
            }]
        }

        with patch.object(phoenix_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await phoenix_client.classify("I don't see any point anymore")

            assert result.label == "grief"
            assert result.safety_flag is True

    @pytest.mark.asyncio
    async def test_classify_invalid_emotion_label(self, phoenix_client):
        """Test handling of invalid emotion label from API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "label": "invalid_emotion",
                        "confidence": 0.75,
                        "safety_flag": False
                    })
                }
            }]
        }

        with patch.object(phoenix_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await phoenix_client.classify("Test message")

            # Should default to neutral with reduced confidence
            assert result.label == "neutral"
            assert result.confidence < 0.75

    @pytest.mark.asyncio
    async def test_classify_timeout(self, phoenix_client):
        """Test handling of API timeout."""
        with patch.object(phoenix_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            result = await phoenix_client.classify("Test message")

            # Should return neutral fallback
            assert result.label == "neutral"
            assert result.confidence == 0.3
            assert result.safety_flag is False

    @pytest.mark.asyncio
    async def test_classify_api_error(self, phoenix_client):
        """Test handling of API error."""
        with patch.object(phoenix_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "API Error",
                request=Mock(),
                response=Mock(status_code=500)
            )

            result = await phoenix_client.classify("Test message")

            # Should return neutral fallback
            assert result.label == "neutral"
            assert result.confidence == 0.3

    @pytest.mark.asyncio
    async def test_classify_malformed_response(self, phoenix_client):
        """Test handling of malformed API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "not valid json"
                }
            }]
        }

        with patch.object(phoenix_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await phoenix_client.classify("Test message")

            # Should return neutral fallback
            assert result.label == "neutral"
            assert result.confidence == 0.3

    def test_build_payload_without_prosody(self, phoenix_client):
        """Test payload building without prosody context."""
        payload = phoenix_client._build_payload("Hello world", None)

        assert payload["model"] == "gpt-4o-mini"
        assert payload["temperature"] == 0.1
        assert payload["response_format"] == {"type": "json_object"}
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert "Hello world" in payload["messages"][1]["content"]
        assert "additional_context" not in payload["messages"][1]["content"]

    def test_build_payload_with_prosody(self, phoenix_client):
        """Test payload building with prosody context."""
        payload = phoenix_client._build_payload(
            "I'm excited!",
            "pitch: high, energy: high"
        )

        user_message = payload["messages"][1]["content"]
        assert "I'm excited!" in user_message
        assert "additional_context" in user_message
        assert "pitch: high" in user_message

    def test_parse_response_success(self, phoenix_client):
        """Test successful response parsing."""
        response_data = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "label": "joy",
                        "confidence": 0.90,
                        "safety_flag": False
                    })
                }
            }]
        }

        result = phoenix_client._parse_response(response_data)

        assert result.label == "joy"
        assert result.confidence == 0.90
        assert result.safety_flag is False
        assert result.raw == response_data

    def test_parse_response_confidence_clamping(self, phoenix_client):
        """Test confidence value is clamped to [0.0, 1.0]."""
        response_data = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "label": "calm",
                        "confidence": 1.5,  # Invalid: too high
                        "safety_flag": False
                    })
                }
            }]
        }

        result = phoenix_client._parse_response(response_data)

        assert result.confidence == 1.0  # Clamped to max

    def test_parse_response_missing_fields(self, phoenix_client):
        """Test parsing with missing fields uses defaults."""
        response_data = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        # Missing label, confidence, safety_flag
                    })
                }
            }]
        }

        result = phoenix_client._parse_response(response_data)

        assert result.label == "neutral"
        assert result.confidence == 0.5
        assert result.safety_flag is False

    @pytest.mark.asyncio
    async def test_context_manager(self, phoenix_config):
        """Test async context manager usage."""
        async with PhoenixClient(phoenix_config) as client:
            assert client is not None
            assert client.client is not None

        # Client should be closed after context
        # Note: httpx client should be closed, but we can't easily verify
        # without accessing internal state

    @pytest.mark.asyncio
    async def test_close(self, phoenix_client):
        """Test explicit close method."""
        await phoenix_client.close()
        # Client should be closed after calling close()
