import logging
from typing import Dict, Any
from app.langgraph_nodes import SophiaLangGraph
from app.services.evaluations import evaluation_manager

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

# Singleton instance
langgraph_service = LangGraphService()