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
                           run_evaluation: bool = True) -> Dict[str, Any]:
        """Process conversation through LangGraph pipeline"""
        
        logger.info(f"Processing conversation through LangGraph for session {session_id}")
        
        try:
            # Run through LangGraph
            final_state = self.sophia_graph.process_conversation(audio_bytes, session_id)
            
            # Run evaluations if requested
            evaluation_report = None
            if run_evaluation:
                try:
                    evaluation_report = evaluation_manager.evaluate_session(
                        session_id=final_state["session_id"],
                        query=final_state["transcript"],
                        answer=final_state["llm_response"],
                        user_audio=final_state["audio_bytes"],
                        sophia_audio=final_state.get("tts_bytes", b""),
                        retrieved_context=""  # Would include RAG context if available
                    )
                    logger.info("Evaluation completed successfully")
                except Exception as e:
                    logger.error(f"Evaluation failed: {e}")
            
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
                "evaluation_report": evaluation_report.__dict__ if evaluation_report else None
            }
            
            logger.info(f"LangGraph conversation processed successfully for session {final_state['session_id']}")
            return response
            
        except Exception as e:
            logger.error(f"LangGraph conversation processing failed: {e}")
            raise

# Singleton instance
langgraph_service = LangGraphService()