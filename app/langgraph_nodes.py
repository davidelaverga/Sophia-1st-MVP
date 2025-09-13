import base64
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, TypedDict
from dataclasses import dataclass

from langgraph.graph import StateGraph, START, END
from langchain.schema import BaseMessage, HumanMessage, AIMessage

from app.services.mistral import transcribe_audio_with_voxtral, generate_llm_reply
from app.services.emotion import analyze_emotion_audio
from app.services.tts import synthesize_inworld
from app.services.supabase import upload_audio_and_get_url, get_supabase
from app.services.memory import memory_manager, ConversationTurn
from app.services.rag import rag_system
from app.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class EmotionData:
    label: str
    confidence: float

class GraphState(TypedDict):
    session_id: str
    audio_bytes: bytes
    transcript: str
    user_emotion: EmotionData
    intent: str
    context_memory: Dict[str, Any]
    llm_response: str
    sophia_emotion: EmotionData
    audio_url: str
    tts_bytes: bytes
    evaluation_logs: List[Dict[str, Any]]
    fallback_used: Dict[str, str]

class AudioIngestor:
    """Takes audio and returns text + user emotion"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def __call__(self, state: GraphState) -> GraphState:
        logger.info(f"AudioIngestor processing session {state['session_id']}")
        
        try:
            # Transcribe using Voxtral + Phoenix emotion analysis
            transcript = transcribe_audio_with_voxtral(state["audio_bytes"])
            user_emotion = analyze_emotion_audio(state["audio_bytes"])
            
            state["transcript"] = transcript
            state["user_emotion"] = EmotionData(
                label=user_emotion.label, 
                confidence=user_emotion.confidence
            )
            
            logger.info(f"AudioIngestor completed: transcript='{transcript[:50]}...', "
                       f"emotion={user_emotion.label}({user_emotion.confidence:.2f})")
            
        except Exception as e:
            logger.error(f"AudioIngestor failed: {e}")
            # Set fallback flag and try Whisper fallback
            state["fallback_used"]["stt"] = "whisper_fallback"
            state["transcript"] = self._whisper_fallback(state["audio_bytes"])
            # Still analyze emotion with Phoenix
            user_emotion = analyze_emotion_audio(state["audio_bytes"])
            state["user_emotion"] = EmotionData(
                label=user_emotion.label, 
                confidence=user_emotion.confidence
            )
        
        return state
    
    def _whisper_fallback(self, audio_bytes: bytes) -> str:
        """Fallback to OpenAI Whisper for STT"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.settings.OPENAI_API_KEY)
            
            # Convert bytes to file-like object
            import io
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            return transcript.text
        except Exception as e:
            logger.error(f"Whisper fallback failed: {e}")
            return ""

class IntentAnalyzer:
    """Classifies user intent (DeFi question, emotional support, small talk)"""
    
    def __call__(self, state: GraphState) -> GraphState:
        logger.info(f"IntentAnalyzer processing session {state['session_id']}")
        
        transcript = state["transcript"]
        
        # Simple rule-based intent classification
        intent = self._classify_intent(transcript)
        state["intent"] = intent
        
        logger.info(f"IntentAnalyzer completed: intent={intent}")
        return state
    
    def _classify_intent(self, text: str) -> str:
        """Simple intent classification"""
        text_lower = text.lower()
        
        defi_keywords = ["defi", "yield", "staking", "liquidity", "farming", "token", 
                        "swap", "protocol", "apy", "apr", "pool", "vault", "ethereum"]
        
        emotional_keywords = ["sad", "worried", "anxious", "happy", "excited", 
                             "confused", "frustrated", "help me"]
        
        if any(keyword in text_lower for keyword in defi_keywords):
            return "defi_question"
        elif any(keyword in text_lower for keyword in emotional_keywords):
            return "emotional_support"
        else:
            return "small_talk"

class ResponseGenerator:
    """Decides what to say and how to say it"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def __call__(self, state: GraphState) -> GraphState:
        logger.info(f"ResponseGenerator processing session {state['session_id']}")
        
        try:
            # Get context from memory
            context = self._build_context(state)
            
            # Generate LLM response with context
            response = self._generate_with_context(
                state["transcript"], 
                state["intent"], 
                state["user_emotion"],
                context
            )
            
            state["llm_response"] = response
            logger.info(f"ResponseGenerator completed: response='{response[:50]}...'")
            
        except Exception as e:
            logger.error(f"ResponseGenerator Mistral failed: {e}")
            # Fallback to Claude-3
            state["fallback_used"]["llm"] = "claude_fallback"
            response = self._claude_fallback(state["transcript"], state["intent"])
            state["llm_response"] = response
        
        return state
    
    def _build_context(self, state: GraphState) -> str:
        """Build context from memory and current state"""
        # Get context from memory manager
        context = memory_manager.get_context_for_llm(state["session_id"])
        state["context_memory"] = context
        
        context_parts = []
        if "last_topics" in context and context["last_topics"]:
            context_parts.append(f"Previous topics: {', '.join(context['last_topics'])}")
        if "last_user_tone" in context:
            context_parts.append(f"User's recent emotional state: {context['last_user_tone']}")
        if "recent_intents" in context and context["recent_intents"]:
            context_parts.append(f"Recent conversation types: {', '.join(context['recent_intents'])}")
        
        return " | ".join(context_parts) if context_parts else ""
    
    def _generate_with_context(self, transcript: str, intent: str, user_emotion: EmotionData, context: str) -> str:
        """Generate response with context and emotion awareness"""
        # Get RAG context for DeFi questions
        rag_context = ""
        if intent == "defi_question":
            rag_context = rag_system.get_context_for_llm(transcript)
            logger.info(f"RAG context retrieved: {len(rag_context)} characters")
        
        # Enhanced prompt based on intent and emotion
        if intent == "defi_question":
            system_prompt = "You are Sophia, a knowledgeable DeFi mentor. Use the provided FAQ context to give accurate, educational responses about DeFi concepts. Keep responses under 50 words."
        elif intent == "emotional_support":
            system_prompt = "You are Sophia, an empathetic AI companion. Provide supportive and encouraging responses. Keep responses under 50 words."
        else:
            system_prompt = "You are Sophia, a friendly AI assistant. Engage in casual conversation. Keep responses under 50 words."
        
        # Build comprehensive prompt
        prompt_parts = [f"The user seems {user_emotion.label} (confidence: {user_emotion.confidence:.2f})."]
        
        if context:
            prompt_parts.append(f"Conversation context: {context}")
        
        if rag_context:
            prompt_parts.append(f"Relevant knowledge base:\n{rag_context}")
        
        prompt_parts.append(f"User question: {transcript}")
        
        full_prompt = " | ".join(prompt_parts)
        
        return generate_llm_reply(full_prompt)
    
    def _claude_fallback(self, transcript: str, intent: str) -> str:
        """Fallback to Claude-3 if Mistral fails"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)
            
            # Build system prompt based on intent
            if intent == "defi_question":
                system_prompt = "You are Sophia, a knowledgeable DeFi mentor. Provide clear, educational responses about DeFi concepts. Keep responses under 50 words."
            elif intent == "emotional_support":
                system_prompt = "You are Sophia, an empathetic AI companion. Provide supportive and encouraging responses. Keep responses under 50 words."
            else:
                system_prompt = "You are Sophia, a friendly AI assistant. Engage in casual conversation. Keep responses under 50 words."
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                system=system_prompt,
                messages=[{"role": "user", "content": transcript}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Claude fallback failed: {e}")
            return "I apologize, but I'm having technical difficulties. Please try again."

class TTSNode:
    """Converts response to audio + analyzes Sophia's emotion"""
    
    def __call__(self, state: GraphState) -> GraphState:
        logger.info(f"TTSNode processing session {state['session_id']}")
        
        try:
            # Synthesize with Inworld/Boson AI
            tts_bytes = synthesize_inworld(state["llm_response"])
            
            # Upload and get URL
            file_name = f"sophia_{int(time.time()*1000)}_{state['session_id']}.mp3"
            audio_url = upload_audio_and_get_url(file_bytes=tts_bytes, file_name=file_name)
            
            # Analyze Sophia's emotion from TTS output
            sophia_emotion = analyze_emotion_audio(tts_bytes)
            
            state["tts_bytes"] = tts_bytes
            state["audio_url"] = audio_url
            state["sophia_emotion"] = EmotionData(
                label=sophia_emotion.label,
                confidence=sophia_emotion.confidence
            )
            
            logger.info(f"TTSNode completed: audio_url={audio_url}, "
                       f"sophia_emotion={sophia_emotion.label}({sophia_emotion.confidence:.2f})")
            
        except Exception as e:
            logger.error(f"TTSNode Inworld failed: {e}")
            # Fallback to Boson AI or other TTS service
            state["fallback_used"]["tts"] = "boson_fallback"
            try:
                tts_bytes = self._boson_ai_fallback(state["llm_response"])
                file_name = f"sophia_fallback_{int(time.time()*1000)}_{state['session_id']}.mp3"
                audio_url = upload_audio_and_get_url(file_bytes=tts_bytes, file_name=file_name)
                sophia_emotion = analyze_emotion_audio(tts_bytes)
                
                state["tts_bytes"] = tts_bytes
                state["audio_url"] = audio_url
                state["sophia_emotion"] = EmotionData(
                    label=sophia_emotion.label,
                    confidence=sophia_emotion.confidence
                )
            except Exception as fallback_error:
                logger.error(f"TTS fallback also failed: {fallback_error}")
                # Final fallback - empty audio
                state["audio_url"] = ""
                state["sophia_emotion"] = EmotionData(label="neutral", confidence=0.5)
        
        return state
    
    def _boson_ai_fallback(self, text: str) -> bytes:
        """Fallback TTS using Boson AI or OpenAI TTS"""
        try:
            # Try OpenAI TTS as fallback
            import openai
            client = openai.OpenAI(api_key=get_settings().OPENAI_API_KEY)
            
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="mp3"
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Boson AI fallback failed: {e}")
            # Return empty bytes as final fallback
            return b""

class EvalLogger:
    """Logs latency, emotions, and fallbacks"""
    
    def __call__(self, state: GraphState) -> GraphState:
        logger.info(f"EvalLogger processing session {state['session_id']}")
        
        # Create evaluation log entry
        eval_entry = {
            "session_id": state["session_id"],
            "timestamp": time.time(),
            "user_emotion": {
                "label": state["user_emotion"].label,
                "confidence": state["user_emotion"].confidence
            },
            "sophia_emotion": {
                "label": state["sophia_emotion"].label, 
                "confidence": state["sophia_emotion"].confidence
            },
            "intent": state["intent"],
            "fallbacks_used": state.get("fallback_used", {}),
            "transcript_length": len(state["transcript"]),
            "response_length": len(state["llm_response"])
        }
        
        # Add to evaluation logs
        if "evaluation_logs" not in state:
            state["evaluation_logs"] = []
        state["evaluation_logs"].append(eval_entry)
        
        # Update session memory
        conversation_turn = ConversationTurn(
            query=state["transcript"],
            response=state["llm_response"],
            user_emotion=state["user_emotion"].label,
            sophia_emotion=state["sophia_emotion"].label,
            intent=state["intent"],
            timestamp=time.time()
        )
        memory_manager.update_session_memory(state["session_id"], conversation_turn)
        
        # Log to console for debugging
        logger.info(f"EvalLogger completed: {eval_entry}")
        
        return state

class SophiaLangGraph:
    """Main LangGraph orchestrator"""
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        # Initialize nodes
        audio_ingestor = AudioIngestor()
        intent_analyzer = IntentAnalyzer()
        response_generator = ResponseGenerator()
        tts_node = TTSNode()
        eval_logger = EvalLogger()
        
        # Create state graph
        workflow = StateGraph(GraphState)
        
        # Add nodes
        workflow.add_node("audio_ingestor", audio_ingestor)
        workflow.add_node("intent_analyzer", intent_analyzer)
        workflow.add_node("response_generator", response_generator)
        workflow.add_node("tts_node", tts_node)
        workflow.add_node("eval_logger", eval_logger)
        
        # Define edges (workflow sequence)
        workflow.add_edge(START, "audio_ingestor")
        workflow.add_edge("audio_ingestor", "intent_analyzer")
        workflow.add_edge("intent_analyzer", "response_generator")
        workflow.add_edge("response_generator", "tts_node")
        workflow.add_edge("tts_node", "eval_logger")
        workflow.add_edge("eval_logger", END)
        
        return workflow.compile()
    
    def process_conversation(self, audio_bytes: bytes, session_id: Optional[str] = None) -> GraphState:
        """Process a complete conversation turn through the graph"""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Initialize state
        initial_state: GraphState = {
            "session_id": session_id,
            "audio_bytes": audio_bytes,
            "transcript": "",
            "user_emotion": EmotionData(label="neutral", confidence=0.0),
            "intent": "",
            "context_memory": {},
            "llm_response": "",
            "sophia_emotion": EmotionData(label="neutral", confidence=0.0),
            "audio_url": "",
            "tts_bytes": b"",
            "evaluation_logs": [],
            "fallback_used": {}
        }
        
        logger.info(f"Starting LangGraph processing for session {session_id}")
        
        # Execute the graph
        final_state = self.graph.invoke(initial_state)
        
        logger.info(f"LangGraph processing completed for session {session_id}")
        
        return final_state
    
    def process_text_conversation(self, message: str, session_id: Optional[str] = None) -> GraphState:
        """Process a text-only conversation turn, bypassing audio processing"""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Initialize state with text message directly
        initial_state: GraphState = {
            "session_id": session_id,
            "audio_bytes": b"",  # Empty for text input
            "transcript": message,  # Use the text message directly
            "user_emotion": EmotionData(label="neutral", confidence=0.7),  # Default for text
            "intent": "",
            "context_memory": {},
            "llm_response": "",
            "sophia_emotion": EmotionData(label="neutral", confidence=0.0),
            "audio_url": "",
            "tts_bytes": b"",
            "evaluation_logs": [],
            "fallback_used": {}
        }
        
        logger.info(f"Starting LangGraph text processing for session {session_id} with message: '{message[:50]}...'")
        
        # Create a text-specific graph that skips audio processing
        text_workflow = StateGraph(GraphState)
        
        # Initialize nodes
        intent_analyzer = IntentAnalyzer()
        response_generator = ResponseGenerator()
        tts_node = TTSNode()
        eval_logger = EvalLogger()
        
        # Add nodes (skip audio_ingestor for text input)
        text_workflow.add_node("intent_analyzer", intent_analyzer)
        text_workflow.add_node("response_generator", response_generator)
        text_workflow.add_node("tts_node", tts_node)
        text_workflow.add_node("eval_logger", eval_logger)
        
        # Define edges (workflow sequence without audio processing)
        text_workflow.add_edge(START, "intent_analyzer")
        text_workflow.add_edge("intent_analyzer", "response_generator")
        text_workflow.add_edge("response_generator", "tts_node")
        text_workflow.add_edge("tts_node", "eval_logger")
        text_workflow.add_edge("eval_logger", END)
        
        # Compile and execute the text-specific graph
        text_graph = text_workflow.compile()
        final_state = text_graph.invoke(initial_state)
        
        logger.info(f"LangGraph text processing completed for session {session_id}")
        
        return final_state