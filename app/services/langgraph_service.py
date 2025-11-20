import logging
from typing import Dict, Any
from app.langgraph_nodes import SophiaLangGraph
from app.services.evaluations import evaluation_manager
from app.services.supabase import insert_conversation_session, insert_emotion_score, insert_conversation_message
import threading

logger = logging.getLogger(__name__)

class LangGraphService:
    """Service wrapper for LangGraph integration"""
    
    def __init__(self):
        self.sophia_graph = SophiaLangGraph()
    
    def process_conversation(self, audio_bytes: bytes, session_id: str = None, 
                           collect_evaluation_data: bool = True) -> Dict[str, Any]:
        """Process conversation through LangGraph pipeline"""
        
        logger.info(f"Processing conversation through LangGraph for session {session_id}")
        
        try:
            # Run through LangGraph
            final_state = self.sophia_graph.process_conversation(audio_bytes, session_id)
            
            # SAVE TO SUPABASE
            try:
                session_data = {
                    "id": final_state["session_id"],
                    "user_id": "00000000-0000-0000-0000-000000000000",
                    "transcript": final_state["transcript"],
                    "response": final_state["llm_response"],
                    "audio_url": final_state.get("audio_url", ""),
                    "user_emotion": {
                        "label": final_state["user_emotion"].label,
                        "confidence": final_state["user_emotion"].confidence
                    },
                    "sophia_emotion": {
                        "label": final_state["sophia_emotion"].label,
                        "confidence": final_state["sophia_emotion"].confidence
                    },
                    "source": "web"
                }
                insert_conversation_session(session_data)
                
                # Save individual messages for multi-turn support
                insert_conversation_message({
                    "session_id": final_state["session_id"],
                    "role": "user",
                    "content": final_state["transcript"],
                    "audio_url": final_state.get("audio_url"),
                    "emotion": {
                        "label": final_state["user_emotion"].label,
                        "confidence": final_state["user_emotion"].confidence
                    }
                })
                
                insert_conversation_message({
                    "session_id": final_state["session_id"],
                    "role": "sophia",
                    "content": final_state["llm_response"],
                    "audio_url": final_state.get("audio_url"),
                    "emotion": {
                        "label": final_state["sophia_emotion"].label,
                        "confidence": final_state["sophia_emotion"].confidence
                    }
                })
                
                # Save emotion scores
                insert_emotion_score(final_state["session_id"], "user", final_state["user_emotion"])
                insert_emotion_score(final_state["session_id"], "sophia", final_state["sophia_emotion"])
                
            except Exception as e:
                logger.error(f"Failed to save conversation to Supabase: {e}")
            
            # Collect evaluation data if requested (instead of running full evaluation)
            if collect_evaluation_data:
                try:
                    evaluation_manager.collect_message_data(
                        session_id=final_state["session_id"],
                        query=final_state["transcript"],
                        answer=final_state["llm_response"],
                        user_audio=final_state["audio_bytes"],
                        sophia_audio=final_state.get("tts_bytes", b""),
                        retrieved_context=""  # Would include RAG context if available
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
                "user_emotion": {
                    "label": final_state["user_emotion"].label,
                    "confidence": final_state["user_emotion"].confidence
                },
                "sophia_emotion": {
                    "label": final_state["sophia_emotion"].label,
                    "confidence": final_state["sophia_emotion"].confidence
                },
                "audio_url": final_state["audio_url"],
                "intent": final_state["intent"],
                "context_memory": final_state.get("context_memory", {}),
                "fallbacks_used": final_state.get("fallback_used", {}),
                "evaluation_logs": final_state.get("evaluation_logs", []),
                "active_conversations": evaluation_manager.get_active_conversation_count(),
                "conversation_status": evaluation_manager.get_conversation_status(final_state["session_id"])
            }
            
            logger.info(f"LangGraph conversation processed successfully for session {final_state['session_id']}")
            return response
            
        except Exception as e:
            logger.error(f"LangGraph conversation processing failed: {e}")
            raise
    
    def process_text_conversation(self, message: str, session_id: str = None, 
                                collect_evaluation_data: bool = True) -> Dict[str, Any]:
        """Process text-only conversation through LangGraph pipeline"""
        
        logger.info(f"Processing text conversation through LangGraph for session {session_id}")
        
        try:
            # Run through LangGraph with text input
            final_state = self.sophia_graph.process_text_conversation(message, session_id)
            
            # SAVE TO SUPABASE
            try:
                # Check if session already exists in database
                session_exists = False
                if session_id:  # User provided a session_id
                    # Check if it exists in DB
                    from app.services.supabase import get_supabase
                    supabase = get_supabase()
                    try:
                        result = supabase.table("conversation_sessions").select("id").eq(
                            "id", final_state["session_id"]
                        ).execute()
                        session_exists = bool(result.data)
                    except Exception:
                        session_exists = False
                
                # Insert session ONLY if it's new
                if not session_exists:
                    try:
                        session_data = {
                            "id": final_state["session_id"],
                            "user_id": "00000000-0000-0000-0000-000000000000",
                            "transcript": final_state["transcript"],
                            "response": final_state["llm_response"],
                            "audio_url": final_state.get("audio_url", ""),
                            "user_emotion": {
                                "label": final_state["user_emotion"].label,
                                "confidence": final_state["user_emotion"].confidence
                            },
                            "sophia_emotion": {
                                "label": final_state["sophia_emotion"].label,
                                "confidence": final_state["sophia_emotion"].confidence
                            },
                            "source": "web"
                        }
                        insert_conversation_session(session_data)
                        logger.info(f"✅ New session created: {final_state['session_id']}")
                    except Exception as session_error:
                        # Log but continue - session might have been created by another request
                        logger.warning(f"⚠️ Session insert failed (may already exist): {session_error}")
                else:
                    logger.info(f"✅ Continuing existing session: {final_state['session_id']}")
                
                # ALWAYS save individual messages (for multi-turn)
                try:
                    insert_conversation_message({
                        "session_id": final_state["session_id"],
                        "role": "user",
                        "content": final_state["transcript"],
                        "emotion": {
                            "label": final_state["user_emotion"].label,
                            "confidence": final_state["user_emotion"].confidence
                        }
                    })
                    logger.info(f"✅ User message saved to conversation_messages")
                except Exception as msg_error:
                    logger.error(f"❌ Failed to save user message: {msg_error}")
                
                try:
                    insert_conversation_message({
                        "session_id": final_state["session_id"],
                        "role": "sophia",
                        "content": final_state["llm_response"],
                        "audio_url": final_state.get("audio_url"),
                        "emotion": {
                            "label": final_state["sophia_emotion"].label,
                            "confidence": final_state["sophia_emotion"].confidence
                        }
                    })
                    logger.info(f"✅ Sophia message saved to conversation_messages")
                except Exception as msg_error:
                    logger.error(f"❌ Failed to save sophia message: {msg_error}")
                
                # Save emotion scores
                try:
                    insert_emotion_score(final_state["session_id"], "user", final_state["user_emotion"])
                    insert_emotion_score(final_state["session_id"], "sophia", final_state["sophia_emotion"])
                except Exception as emotion_error:
                    logger.warning(f"⚠️ Failed to save emotion scores: {emotion_error}")
                
            except Exception as e:
                logger.error(f"❌ Failed to save conversation to Supabase: {e}")
            
            # Collect evaluation data if requested
            if collect_evaluation_data:
                try:
                    evaluation_manager.collect_message_data(
                        session_id=final_state["session_id"],
                        query=final_state["transcript"],
                        answer=final_state["llm_response"],
                        user_audio=b"",  # No audio for text input
                        sophia_audio=final_state.get("tts_bytes", b""),
                        retrieved_context=""  # Would include RAG context if available
                    )
                    logger.info("Evaluation data collected successfully")
                except Exception as e:
                    logger.error(f"Failed to collect evaluation data: {e}")
        
            # Check for finished conversations and run evaluations
            try:
                finished_reports = evaluation_manager.check_and_evaluate_finished_conversations()
                if finished_reports:
                    logger.info(f"Completed evaluations for {len(finished_reports)} finished conversations")
            except Exception as e:
                logger.error(f"Failed to check finished conversations: {e}")
            
            # Format response
            response = {
                "session_id": final_state["session_id"],
                "transcript": final_state["transcript"],
                "reply": final_state["llm_response"],
                "user_emotion": {
                    "label": final_state["user_emotion"].label,
                    "confidence": final_state["user_emotion"].confidence
                },
                "sophia_emotion": {
                    "label": final_state["sophia_emotion"].label,
                    "confidence": final_state["sophia_emotion"].confidence
                },
                "audio_url": final_state["audio_url"],
                "intent": final_state["intent"],
                "context_memory": final_state.get("context_memory", {}),
                "fallbacks_used": final_state.get("fallback_used", {}),
                "evaluation_logs": final_state.get("evaluation_logs", []),
                "active_conversations": evaluation_manager.get_active_conversation_count(),
                "conversation_status": evaluation_manager.get_conversation_status(final_state["session_id"])
            }
            
            logger.info(f"LangGraph text conversation processed successfully for session {final_state['session_id']}")
            return response
            
        except Exception as e:
            logger.error(f"LangGraph text conversation processing failed: {e}")
            raise

    def stream_conversation_response(self, audio_bytes: bytes, session_id: str = None):
        """Stream conversation response through LangGraph pipeline
        
        Flow: Audio → Voxtral ASR → Mistral LLM (streaming)
        """
        
        logger.info(f"Streaming conversation through LangGraph for session {session_id}")
        
        try:
            # Process audio to get context (ASR + emotion + intent + RAG)
            state = self.sophia_graph.process_audio_to_context(audio_bytes, session_id)
            
            # Stream LLM response using the processed context
            for token in self.sophia_graph.stream_llm_response(state):
                yield token
                
        except Exception as e:
            logger.error(f"LangGraph streaming failed: {e}")
            # Fallback to rule-based response
            yield "I'm having trouble processing your request. Could you please try again?"

    def _run_eval_checks_background(self):
        """Run evaluation checks in background thread"""
        try:
            evaluation_manager.check_and_run_evaluations()
        except Exception as e:
            logger.error(f"Background evaluation check failed: {e}")

# Singleton instance
langgraph_service = LangGraphService()