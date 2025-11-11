"""Emotional RAG provider with S2-P8 service integration and YAML fallback."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from app.config import get_settings

logger = logging.getLogger(__name__)


class _StaticGuidanceStore:
    """Loads emotional guidance YAML into an immutable, constant-time lookup map."""

    def __init__(self, yaml_path: Path):
        self._yaml_path = yaml_path
        self._guidance_map = self._load_yaml(yaml_path)
        if "neutral" not in self._guidance_map:
            raise ValueError("Emotional guidance YAML must define a 'neutral' entry.")

    @staticmethod
    def _load_yaml(yaml_path: Path) -> Dict[str, List[str]]:
        guidance_map: Dict[str, List[str]] = {}
        current_key: Optional[str] = None

        def _normalize(value: str) -> str:
            stripped = value.strip()
            if stripped.startswith(('"', "'")) and stripped.endswith(
                ('"', "'")
            ):
                stripped = stripped[1:-1]
            return stripped.strip()

        with yaml_path.open("r", encoding="utf-8") as fp:
            for raw_line in fp:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if not line.startswith("-") and line.endswith(":"):
                    current_key = line[:-1].strip().lower()
                    if current_key:
                        guidance_map.setdefault(current_key, [])
                    continue
                if line.startswith("-"):
                    if not current_key:
                        continue
                    value = _normalize(line[1:])
                    if value:
                        guidance_map.setdefault(current_key, []).append(value)

        return guidance_map

    def get(self, emotion: str) -> List[str]:
        emotion_key = (emotion or "neutral").strip().lower()
        if emotion_key in self._guidance_map:
            return self._guidance_map[emotion_key]
        return self._guidance_map.get("neutral", [])


HttpPostFn = Callable[[str, Dict[str, Any], float], Dict[str, Any]]


class EmotionalGuidanceProvider:
    """Facade that picks S2-P8 service or static YAML at runtime."""

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        service_url: Optional[str] = None,
        yaml_path: Optional[Path] = None,
        timeout_seconds: Optional[float] = None,
        http_post: Optional[HttpPostFn] = None,
    ):
        settings = get_settings()
        default_mode = settings.EMO_RAG_PROVIDER or "static"
        default_timeout = (
            settings.EMOTIONAL_RAG_TIMEOUT_SECONDS
            if hasattr(settings, "EMOTIONAL_RAG_TIMEOUT_SECONDS")
            else 0.3
        )

        self._mode = (mode or default_mode).strip().lower()
        self._service_url = service_url or settings.EMOTIONAL_RAG_SERVICE_URL
        self._timeout = timeout_seconds or default_timeout
        self._http_post = http_post or self._default_http_post

        default_yaml_path = Path(__file__).resolve().parents[1] / "data" / "emotional_guidance.yaml"
        self._static_store = _StaticGuidanceStore(yaml_path or default_yaml_path)

    def get_guidance(self, emotion: Optional[str]) -> List[str]:
        """Return guidance for an emotion, falling back to YAML if service is unavailable."""
        normalized_emotion = (emotion or "neutral").strip().lower()
        start = time.perf_counter()
        source = "static"

        try:
            if self._mode == "service":
                guidance = self._fetch_remote_guidance(normalized_emotion)
                source = "service"
            else:
                guidance = None
        except Exception as exc:
            logger.warning(
                "Emotional guidance service failed for %s: %s. Using YAML fallback.",
                normalized_emotion,
                exc,
            )
            guidance = None

        if not guidance:
            guidance = self._static_store.get(normalized_emotion)
            source = "static"

        latency_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            "Emotional guidance lookup emotion=%s source=%s latency_ms=%.2f count=%d",
            normalized_emotion,
            source,
            latency_ms,
            len(guidance),
        )
        return guidance

    def _fetch_remote_guidance(self, emotion: str) -> List[str]:
        if not self._service_url:
            raise RuntimeError("EMOTIONAL_RAG_SERVICE_URL is not configured.")

        payload = {"emotion": emotion}
        body = self._http_post(self._service_url, payload, self._timeout)
        if not isinstance(body, dict):
            raise ValueError("Emotional guidance response must be a JSON object.")

        guidance = body.get("guidance")
        if not isinstance(guidance, list):
            raise ValueError("Emotional guidance response missing 'guidance' list.")

        cleaned = [str(item).strip() for item in guidance if isinstance(item, str)]
        return [item for item in cleaned if item]

    def _default_http_post(
        self, url: str, payload: Dict[str, Any], timeout: float
    ) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                body = response.read()
        except urllib.error.HTTPError as http_err:
            raise RuntimeError(f"HTTP error {http_err.code}") from http_err
        except urllib.error.URLError as url_err:
            raise RuntimeError(f"HTTP request failed: {url_err.reason}") from url_err

        if status >= 400:
            raise RuntimeError(f"HTTP error {status}")

        if not body:
            return {}

        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as err:
            raise ValueError("Invalid JSON response for emotional guidance.") from err


_guidance_provider: Optional[EmotionalGuidanceProvider] = None


def get_guidance(emotion: Optional[str]) -> List[str]:
    """Public API that matches S2-P8 service contract."""
    global _guidance_provider
    if _guidance_provider is None:
        _guidance_provider = EmotionalGuidanceProvider()
    return _guidance_provider.get_guidance(emotion)


def override_guidance_provider(provider: Optional[EmotionalGuidanceProvider]) -> None:
    """Enable tests to swap the provider implementation."""
    global _guidance_provider
    _guidance_provider = provider


def format_guidance_block(guidance: Sequence[str]) -> str:
    """Return a formatted bullet block for inclusion in prompts."""
    cleaned = [item.strip() for item in guidance if isinstance(item, str) and item.strip()]
    if not cleaned:
        return ""
    return "Emotion guidance cues:\n- " + "\n- ".join(cleaned)


def build_emotion_guided_prompt(
    message: str,
    emotion_label: str,
    emotion_confidence: float,
    guidance: Sequence[str],
    *,
    max_words: int = 60,
) -> str:
    """Compose an instruction string that carries emotion cues into downstream prompts."""
    safe_label = (emotion_label or "neutral").strip() or "neutral"
    safe_conf = emotion_confidence if emotion_confidence is not None else 0.0
    safe_message = (message or "").strip()

    prompt_parts = [
        f"The user seems {safe_label} (confidence: {safe_conf:.2f}).",
    ]

    guidance_block = format_guidance_block(guidance)
    if guidance_block:
        prompt_parts.append(guidance_block)

    if safe_message:
        prompt_parts.append(f"User question: {safe_message}")
    else:
        prompt_parts.append("User question: (no text provided)")

    prompt_parts.append(
        f"Respond as Sophia with empathy while staying concise (<= {max_words} words)."
    )

    return " | ".join(part for part in prompt_parts if part)
