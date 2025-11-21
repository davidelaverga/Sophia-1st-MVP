"""Wrapper service that executes SophiaLangGraph and coordinates evaluation flows."""

import logging
from typing import Dict, Any, Optional
from app.langgraph_nodes import SophiaLangGraph
from app.services.evaluations import evaluation_manager
import threading

logger = logging.getLogger(__name__)


class LangGraphService:
    """Service wrapper for LangGraph integration"""

    def __init__(self):
        self.sophia_graph = SophiaLangGraph()

    def process_conversation(
        self,
        audio_bytes: bytes,
        session_id: str = None,
        collect_evaluation_data: bool = True,
        supabase_token: Optional[str] = None,
        cancel_check=None,
    ) -> Dict[str, Any]:
        """Process conversation through LangGraph pipeline"""

        logger.info(
            f"Processing conversation through LangGraph for session {session_id}"
        )

        try:
            # Run through LangGraph
            final_state = self.sophia_graph.process_conversation(
                audio_bytes,
                session_id,
                supabase_token=supabase_token,
                cancel_check=cancel_check,
            )

            # Collect evaluation data if requested (instead of running full evaluation)
            if collect_evaluation_data:
                try:
                    evaluation_manager.collect_message_data(
                        session_id=final_state["session_id"],
                        query=final_state["transcript"],
                        answer=final_state["llm_response"],
                        user_audio=final_state["audio_bytes"],
                        sophia_audio=final_state.get("tts_bytes", b""),
                        retrieved_context="",  # Would include RAG context if available
                    )
                    logger.info("Evaluation data collected successfully")
                except Exception as e:
                    logger.error(f"Failed to collect evaluation data: {e}")

            # Check for finished conversations and run evaluations
            try:
                threading.Thread(
                    target=self._run_eval_checks_background,
                    name="eval-check-finished",
                    daemon=True,
                ).start()
            except Exception as e:
                logger.error(f"Failed to start evaluation background task: {e}")

            # Format response
            response = {
                "session_id": final_state["session_id"],
                "transcript": final_state["transcript"],
                "reply": final_state["llm_response"],
                "response_path": final_state.get("response_path"),
                "user_emotion": {
                    "label": final_state["user_emotion"].label,
                    "confidence": final_state["user_emotion"].confidence,
                },
                "sophia_emotion": {
                    "label": final_state["sophia_emotion"].label,
                    "confidence": final_state["sophia_emotion"].confidence,
                },
                "is_mock_audio": final_state["is_mock_audio"],
                "audio_url": final_state["audio_url"],
                "intent": final_state["intent"],
                "context_memory": final_state.get("context_memory", {}),
                "fallbacks_used": final_state.get("fallback_used", {}),
                "evaluation_logs": final_state.get("evaluation_logs", []),
                "active_conversations": evaluation_manager.get_active_conversation_count(),
                "conversation_status": evaluation_manager.get_conversation_status(
                    final_state["session_id"]
                ),
            }

            logger.info(
                f"LangGraph conversation processed successfully for session {final_state['session_id']}"
            )
            return response

        except Exception as e:
            logger.error(f"LangGraph conversation processing failed: {e}")
            raise

    def process_text_conversation(
        self,
        message: str,
        session_id: str = None,
        collect_evaluation_data: bool = True,
        supabase_token: Optional[str] = None,
        cancel_check=None,
    ) -> Dict[str, Any]:
        """Process text-only conversation through LangGraph pipeline"""

        logger.info(
            f"Processing text conversation through LangGraph for session {session_id}"
        )

        try:
            # Run through LangGraph with text input
            final_state = self.sophia_graph.process_text_conversation(
                message,
                session_id,
                supabase_token=supabase_token,
                cancel_check=cancel_check,
            )

            # Collect evaluation data if requested
            if collect_evaluation_data:
                try:
                    evaluation_manager.collect_message_data(
                        session_id=final_state["session_id"],
                        query=final_state["transcript"],
                        answer=final_state["llm_response"],
                        user_audio=b"",  # No audio for text input
                        sophia_audio=final_state.get("tts_bytes", b""),
                        retrieved_context="",  # Would include RAG context if available
                    )
                    logger.info("Evaluation data collected successfully")
                except Exception as e:
                    logger.error(f"Failed to collect evaluation data: {e}")

            # Check for finished conversations and run evaluations
            try:
                finished_reports = (
                    evaluation_manager.check_and_evaluate_finished_conversations()
                )
                if finished_reports:
                    logger.info(
                        f"Completed evaluations for {len(finished_reports)} finished conversations"
                    )
            except Exception as e:
                logger.error(f"Failed to check finished conversations: {e}")

            # Format response
            response = {
                "session_id": final_state["session_id"],
                "transcript": final_state["transcript"],
                "reply": final_state["llm_response"],
                "response_path": final_state.get("response_path"),
                "user_emotion": {
                    "label": final_state["user_emotion"].label,
                    "confidence": final_state["user_emotion"].confidence,
                },
                "sophia_emotion": {
                    "label": final_state["sophia_emotion"].label,
                    "confidence": final_state["sophia_emotion"].confidence,
                },
                "audio_url": final_state["audio_url"],
                "is_mock_audio": final_state["is_mock_audio"],
                "intent": final_state["intent"],
                "context_memory": final_state.get("context_memory", {}),
                "fallbacks_used": final_state.get("fallback_used", {}),
                "evaluation_logs": final_state.get("evaluation_logs", []),
                "active_conversations": evaluation_manager.get_active_conversation_count(),
                "conversation_status": evaluation_manager.get_conversation_status(
                    final_state["session_id"]
                ),
            }

            logger.info(
                f"LangGraph text conversation processed successfully for session {final_state['session_id']}"
            )
            return response

        except Exception as e:
            logger.error(f"LangGraph text conversation processing failed: {e}")
            raise

    async def stream_conversation_response(
        self, audio_bytes: bytes, session_id: str = None
    ):
        """Stream conversation response with tier-0 classification - Task #42537"""

        logger.info(
            f"Streaming conversation with tier-0 classifier for session {session_id}"
        )

        try:
            # Step 1: STT to get transcript
            from app.services.mistral import transcribe_audio_with_voxtral

            transcript = transcribe_audio_with_voxtral(audio_bytes)
            logger.info(f"📝 Transcript ({len(transcript)} chars): '{transcript}'")

            # Step 2: Tier-0 Fast Classifier (Task #42537)
            tier0_result = None
            try:
                from app.services.tier0_classifier import classify_tier0_fast

                # Call async function directly with await (now that we're in async generator)
                result = await classify_tier0_fast(
                    transcript, prosody=None, timeout_ms=500
                )

                logger.info(
                    f"🎯 Tier-0: intent={result.type}, emotion={result.emotion}, "
                    f"confidence={result.confidence:.2f}, latency={result.latency_ms}ms, "
                    f"source={result.source}"
                )

                # Send tier-0 results to frontend as first yield
                tier0_result = {
                    "__tier0__": True,
                    "transcript": transcript,
                    "intent": result.type,
                    "emotion": result.emotion,
                    "confidence": result.confidence,
                    "latency_ms": result.latency_ms,
                    "source": result.source,
                }
                yield tier0_result

                # Check for crisis
                if result.type == "crisis":
                    logger.warning(f"🚨 CRISIS DETECTED in session {session_id}")
                    yield "I'm very concerned about what you're sharing. Please reach out to a crisis helpline immediately. "
                    yield "In the US: 988 (Suicide & Crisis Lifeline). You matter, and help is available 24/7."
                    return

            except Exception as e:
                logger.warning(
                    f"Tier-0 classifier failed: {e}, continuing without classification"
                )

            # Step 3: Generate response with streaming
            from app.services.mistral import stream_generate_reply_from_audio

            for token in stream_generate_reply_from_audio(audio_bytes):
                yield token

        except Exception as e:
            logger.error(f"Conversation streaming failed: {e}")
            # Fallback to rule-based response
            yield "I'm having trouble processing your request. Could you please try again?"

    def stream_conversation_response_old(
        self, audio_bytes: bytes, session_id: str = None
    ):
        """Stream conversation response through LangGraph pipeline

        Flow: Audio → Voxtral ASR → Mistral LLM (streaming)
        """

        logger.info(
            f"Streaming conversation through LangGraph for session {session_id}"
        )

        try:
            # Process audio to get context (ASR + emotion + intent + RAG)
            state = self.sophia_graph.process_audio_to_context(audio_bytes, session_id)

            # Stream LLM response using the processed context
            for token in self.sophia_graph.stream_llm_response(state):
                yield token

        except Exception as e:
            logger.error(f"LangGraph streaming failed: {e}")
            yield "I'm having trouble processing your request. Could you please try again?"

    def _run_eval_checks_background(self):
        """Run evaluation checks in background thread"""
        try:
            evaluation_manager.check_and_run_evaluations()
        except Exception as e:
            logger.error(f"Background evaluation check failed: {e}")


# Singleton instance
langgraph_service = LangGraphService()
