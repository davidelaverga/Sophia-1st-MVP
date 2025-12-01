"""Voxtral Large service offering unified audio-to-response handling with intelligent fallbacks."""

import base64
import io
import logging
from typing import Optional, Generator, Dict, Any, Callable
from mistralai import Mistral
from app.config import get_settings

logger = logging.getLogger(__name__)

CancelCallback = Callable[[], None]


def _noop_cancel() -> None:
    return None


def _ensure_cancel(cb: Optional[CancelCallback]) -> CancelCallback:
    return cb if cb is not None else _noop_cancel


class VoxtralLargeService:
    """
    Unified audio-to-response service using Voxtral.

    This service processes audio input and generates responses in a single pass,
    eliminating the need for separate STT and LLM coordination.

    For unified audio+text conversations (LIGHT / EMOTIONAL / AGENTIC modes),
    we always use the accurate model. UTILITY_DIRECT uses Voxtral only for
    STT upstream and stays template-based (no unified chat call).
    """

    def __init__(self):
        self.settings = get_settings()
        if not self.settings.MISTRAL_API_KEY:
            raise RuntimeError("MISTRAL_API_KEY is not set")
        self.client = Mistral(api_key=self.settings.MISTRAL_API_KEY)

        # Mode-aware model settings
        self.fast_model = getattr(
            self.settings, "VOXTRAL_FAST_MODEL", "voxtral-mini-latest"
        )
        self.accurate_model = getattr(
            self.settings, "VOXTRAL_ACCURATE_MODEL", "voxtral-small-latest"
        )
        # Default model (legacy callers that don't specify mode)
        self.model = self.accurate_model

        logger.info(
            f"VoxtralLargeService initialized: fast={self.fast_model}, accurate={self.accurate_model}"
        )

    def _select_model(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Select the model for unified audio+text conversations.

        DIRECT mode does not use this unified path; it uses STT-only + templates.
        For now, all unified calls use the accurate model.
        """
        logger.debug(
            "Model selection (unified pipeline): using accurate model (%s)",
            self.accurate_model,
        )
        return self.accurate_model

    def generate_response(
        self,
        audio_bytes: bytes,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        cancel_check: Optional[CancelCallback] = None,
    ) -> str:
        """
        Generate a complete response from audio input using Voxtral.

        Args:
            audio_bytes: Raw audio data
            context: Optional conversation context (memory, intent, emotion, current_mode)
            system_prompt: Optional system instructions

        Returns:
            Generated response text
        """
        cancel = _ensure_cancel(cancel_check)
        cancel()
        try:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            # Build enriched prompt with context
            text_context = self._build_context_prompt(context, system_prompt)

            # Select model based on mode
            selected_model = self._select_model(context)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": audio_b64,
                        },
                        {"type": "text", "text": text_context},
                    ],
                }
            ]

            logger.info(
                f"Calling Voxtral ({selected_model}) with context length: {len(text_context)}"
            )

            response = self.client.chat.complete(
                model=selected_model,
                messages=messages,
            )
            cancel()
            # Extract response content
            content = self._extract_response_content(response)
            logger.info(f"Voxtral ({selected_model}) response: {content[:100]}...")

            return content

        except Exception as e:
            logger.error(f"VoxtralLargeService.generate_response failed: {e}")
            raise

    def stream_response(
        self,
        audio_bytes: bytes,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        cancel_check: Optional[CancelCallback] = None,
    ) -> Generator[str, None, None]:
        """
        Stream response tokens from audio input using Voxtral.

        Args:
            audio_bytes: Raw audio data
            context: Optional conversation context (memory, intent, emotion, current_mode)
            system_prompt: Optional system instructions

        Yields:
            Response text chunks as they're generated
        """
        cancel = _ensure_cancel(cancel_check)
        cancel()
        try:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            # Build enriched prompt with context
            text_context = self._build_context_prompt(context, system_prompt)

            # Select model based on mode
            selected_model = self._select_model(context)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": audio_b64,
                        },
                        {"type": "text", "text": text_context},
                    ],
                }
            ]

            logger.info(
                f"Starting Voxtral ({selected_model}) streaming with context length: {len(text_context)}"
            )

            stream = self.client.chat.stream(
                model=selected_model,
                messages=messages,
            )

            tokens_yielded = 0
            for chunk in stream:
                cancel()
                try:
                    # Handle CompletionEvent wrapper from newer Mistral SDK
                    chunk_data = chunk.data if hasattr(chunk, "data") else chunk

                    # Extract content from various SDK response formats
                    if hasattr(chunk_data, "choices") and chunk_data.choices:
                        delta = chunk_data.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            cancel()
                            yield delta.content
                            tokens_yielded += 1
                    elif hasattr(chunk_data, "delta") and chunk_data.delta:
                        if (
                            hasattr(chunk_data.delta, "content")
                            and chunk_data.delta.content
                        ):
                            cancel()
                            yield chunk_data.delta.content
                            tokens_yielded += 1
                    elif hasattr(chunk_data, "content") and chunk_data.content:
                        cancel()
                        yield chunk_data.content
                        tokens_yielded += 1

                except Exception as e:
                    logger.warning(f"Error processing Voxtral Large stream chunk: {e}")
                    continue

            logger.info(
                f"Voxtral ({selected_model}) streaming completed, yielded {tokens_yielded} tokens"
            )

            if tokens_yielded == 0:
                logger.warning("No tokens yielded from Voxtral stream")
                raise Exception("Empty stream from Voxtral")

        except Exception as e:
            logger.error(f"VoxtralLargeService.stream_response failed: {e}")
            raise

    def extract_transcript_and_respond(
        self, audio_bytes: bytes, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Process audio and return both transcript and response.

        This is useful for debugging and when you need both outputs.
        Note: Voxtral Large doesn't provide separate transcript in streaming mode,
        so we use a two-step approach here.

        Args:
            audio_bytes: Raw audio data
            context: Optional conversation context

        Returns:
            Dict with 'transcript' and 'response' keys
        """
        try:
            # First, transcribe to get the text (for debugging/logging)
            transcript = self._transcribe_audio(audio_bytes)

            # Then generate response using the full audio understanding
            response = self.generate_response(audio_bytes, context)

            return {"transcript": transcript, "response": response}

        except Exception as e:
            logger.error(
                f"VoxtralLargeService.extract_transcript_and_respond failed: {e}"
            )
            raise

    def _transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Internal method to transcribe audio when transcript is needed separately.
        Uses Voxtral's transcription endpoint with fast model for low latency.
        """
        try:
            file_name = f"audio{self._detect_audio_extension(audio_bytes)}"
            bio = io.BytesIO(audio_bytes)

            # Always use fast model for transcription (speed priority)
            resp = self.client.audio.transcriptions.complete(
                model=self.fast_model,
                file={
                    "content": bio,
                    "file_name": file_name,
                },
            )

            # Extract transcript text
            for key in ("text", "output_text", "transcript"):
                val = getattr(resp, key, None)
                if isinstance(val, str) and val.strip():
                    return val.strip()

            return str(resp).strip()

        except Exception as e:
            logger.error(f"_transcribe_audio failed: {e}")
            return ""

    def _build_context_prompt(
        self,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Build enriched context prompt from conversation memory and system instructions.

        Args:
            context: Dictionary with conversation context (memory, intent, emotion, rag_context)
            system_prompt: Base system instructions

        Returns:
            Formatted context string
        """
        if not system_prompt:
            system_prompt = (
                "You are Sophia, a knowledgeable and empathetic DeFi mentor. "
                "Provide clear, educational, and supportive responses. "
                "Keep responses under 50 words for voice interaction."
            )

        parts = [system_prompt]

        if context:
            # Add conversation memory
            if "last_topics" in context and context["last_topics"]:
                parts.append(f"Previous topics: {', '.join(context['last_topics'])}")

            # Add emotional context
            if "user_emotion" in context:
                emotion_label = context["user_emotion"].get("label", "neutral")
                emotion_conf = context["user_emotion"].get("confidence", 0.0)
                parts.append(
                    f"User appears {emotion_label} (confidence: {emotion_conf:.2f})"
                )

            if "last_user_tone" in context:
                parts.append(
                    f"User's recent emotional state: {context['last_user_tone']}"
                )

            # Add intent awareness
            if "intent" in context:
                parts.append(f"Query type: {context['intent']}")

            if "recent_intents" in context and context["recent_intents"]:
                parts.append(
                    f"Recent conversation types: {', '.join(context['recent_intents'])}"
                )

            # Add RAG/knowledge base context
            if "rag_context" in context and context["rag_context"]:
                parts.append(f"Relevant knowledge base:\n{context['rag_context']}")

        return " | ".join(parts)

    def _extract_response_content(self, response) -> str:
        """
        Extract text content from Mistral API response.
        Handles various response formats from the SDK.
        """
        try:
            # Try standard chat completion format
            if hasattr(response, "choices") and response.choices:
                message = response.choices[0].message
                content = getattr(message, "content", message)

                # Handle list of content blocks
                if isinstance(content, list):
                    text_parts = []
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            text_parts.append(c.get("text", ""))
                    result = " ".join([t for t in text_parts if t]).strip()
                    if result:
                        return result

                # Handle string content
                return str(content).strip()

            # Fallback to string representation
            return str(response).strip()

        except Exception as e:
            logger.error(f"Error extracting response content: {e}")
            return str(response).strip()

    def _detect_audio_extension(self, data: bytes) -> str:
        """
        Detect audio file extension from magic bytes.
        """
        try:
            if not data or len(data) < 4:
                return ".wav"

            b0 = data[:4]
            if b0 == b"RIFF":
                return ".wav"
            if b0[:3] == b"ID3" or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
                return ".mp3"
            if data[:4] == b"OggS":
                return ".ogg"
            if data[:4] == bytes([0x1A, 0x45, 0xDF, 0xA3]):  # WebM/Matroska EBML
                return ".webm"

            return ".wav"
        except Exception:
            return ".wav"


class HybridVoxtralService:
    """
    Hybrid service with intelligent fallback from Voxtral Large to the legacy pipeline.

    This provides resilience during the transition period and handles rate limiting,
    API errors, or other issues gracefully.
    """

    def __init__(self):
        self.primary = VoxtralLargeService()
        self.settings = get_settings()
        logger.info("HybridVoxtralService initialized with Voxtral Large primary")

    def generate_response(
        self,
        audio_bytes: bytes,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        fallback_on_error: bool = True,
        cancel_check: Optional[CancelCallback] = None,
    ) -> Dict[str, Any]:
        """
        Generate response with automatic fallback.

        Args:
            audio_bytes: Raw audio data
            context: Optional conversation context
            system_prompt: Optional system instructions
            fallback_on_error: Whether to fallback to legacy pipeline on error

        Returns:
            Dict with 'response', 'service_used', and optional 'transcript'
        """
        # Try Voxtral Large first
        cancel = _ensure_cancel(cancel_check)
        try:
            logger.info("Attempting Voxtral Large unified pipeline")
            response = self.primary.generate_response(
                audio_bytes,
                context,
                system_prompt,
                cancel_check=cancel,
            )

            return {
                "response": response,
                "service_used": "voxtral",
                "transcript": None,  # Voxtral unified pipeline doesn't separate these
            }

        except Exception as e:
            logger.warning(f"Voxtral Large failed: {e}")
            cancel()

            if not fallback_on_error:
                raise

            # Fallback to legacy pipeline
            return self._fallback_pipeline(
                audio_bytes, context, system_prompt, cancel_check=cancel
            )

    def stream_response(
        self,
        audio_bytes: bytes,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        fallback_on_error: bool = True,
        cancel_check: Optional[CancelCallback] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream response with automatic fallback.

        Yields:
            Dict with 'token' and 'service_used' keys
        """
        # Try Voxtral Large streaming first
        cancel = _ensure_cancel(cancel_check)
        try:
            logger.info("Attempting Voxtral Large streaming")

            for token in self.primary.stream_response(
                audio_bytes,
                context,
                system_prompt,
                cancel_check=cancel,
            ):
                cancel()
                yield {"token": token, "service_used": "voxtral"}

            return  # Success, no fallback needed

        except Exception as e:
            logger.warning(f"Voxtral Large streaming failed: {e}")
            cancel()

            if not fallback_on_error:
                raise

            # Fallback to legacy streaming
            logger.info("Falling back to legacy STT + LLM streaming")

            try:
                # Import legacy functions
                from app.services.mistral import (
                    transcribe_audio_with_voxtral,
                    stream_generate_llm_reply,
                )

                # Transcribe first
                transcript = transcribe_audio_with_voxtral(
                    audio_bytes,
                    cancel_check=cancel,
                )

                if not transcript:
                    yield {
                        "token": "I couldn't understand the audio. Could you please try again?",
                        "service_used": "fallback_error",
                    }
                    return

                # Build context-aware prompt for legacy LLM
                prompt = self._build_legacy_prompt(transcript, context)

                # Stream tokens from legacy pipeline
                for token in stream_generate_llm_reply(prompt, cancel_check=cancel):
                    cancel()
                    yield {"token": token, "service_used": "legacy_pipeline"}

            except Exception as fallback_error:
                logger.error(f"Fallback streaming also failed: {fallback_error}")
                yield {
                    "token": "I'm experiencing technical difficulties. Please try again shortly.",
                    "service_used": "fallback_error",
                }

    def _fallback_pipeline(
        self,
        audio_bytes: bytes,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        cancel_check: Optional[CancelCallback] = None,
    ) -> Dict[str, Any]:
        """
        Execute legacy STT + LLM pipeline as fallback.
        """
        cancel = _ensure_cancel(cancel_check)
        try:
            logger.info("Executing fallback pipeline (STT + LLM)")

            # Import legacy functions
            from app.services.mistral import (
                transcribe_audio_with_voxtral,
                generate_llm_reply,
            )

            # Transcribe
            transcript = transcribe_audio_with_voxtral(
                audio_bytes,
                cancel_check=cancel,
            )

            if not transcript:
                return {
                    "response": "I couldn't understand the audio. Could you please try again?",
                    "service_used": "fallback_error",
                    "transcript": "",
                }

            # Build context-aware prompt
            prompt = self._build_legacy_prompt(transcript, context)

            # Generate response
            response = generate_llm_reply(prompt, cancel_check=cancel)

            return {
                "response": response,
                "service_used": "legacy_pipeline",
                "transcript": transcript,
            }

        except Exception as e:
            logger.error(f"Fallback pipeline failed: {e}")
            return {
                "response": "I'm experiencing technical difficulties. Please try again shortly.",
                "service_used": "fallback_error",
                "transcript": "",
            }

    def _build_legacy_prompt(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build enriched prompt for legacy LLM pipeline.
        """
        parts = []

        if context:
            if "user_emotion" in context:
                emotion_label = context["user_emotion"].get("label", "neutral")
                parts.append(f"User appears {emotion_label}.")

            if "last_topics" in context and context["last_topics"]:
                parts.append(f"Previous topics: {', '.join(context['last_topics'])}")

            if "rag_context" in context and context["rag_context"]:
                parts.append(f"Knowledge base:\n{context['rag_context']}")

        parts.append(f"User question: {transcript}")

        return " | ".join(parts)
