import base64
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, TypedDict
from dataclasses import dataclass

from langgraph.graph import StateGraph, START, END

from app.services.mistral import transcribe_audio_with_voxtral, generate_llm_reply, generate_llm_reply_with_context
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
    """Transcribes audio using Voxtral and analyzes emotion using Phoenix"""
    
    def __init__(self):
        self.settings = get_settings()
        logger.info("AudioIngestor initialized (Voxtral ASR + Phoenix emotion)")
    
    def __call__(self, state: GraphState) -> GraphState:
        logger.info(f"AudioIngestor processing session {state['session_id']}")
        state.setdefault("fallback_used", {})

        try:
            # Transcribe using Voxtral + Phoenix emotion analysis
            transcript = transcribe_audio_with_voxtral(state["audio_bytes"])
            logger.debug(
                "AudioIngestor: transcribe_audio_with_voxtral returned %s (len=%d)",
                repr(transcript[:75] if isinstance(transcript, str) else transcript),
                len(transcript) if isinstance(transcript, str) else -1,
            )

            # Try Whisper immediately if Voxtral produced an empty transcript
            if not transcript or (isinstance(transcript, str) and not transcript.strip()):
                logger.warning(
                    "AudioIngestor: Voxtral returned empty transcript, trying Whisper fallback"
                )
                state["fallback_used"]["stt"] = "voxtral_empty_whisper_fallback"
                transcript = self._whisper_fallback(state["audio_bytes"])
                whisper_preview = transcript[:50] if isinstance(transcript, str) else transcript
                logger.info(
                    "AudioIngestor: Whisper fallback returned %s (len=%d)",
                    repr(whisper_preview),
                    len(transcript) if isinstance(transcript, str) else -1,
                )

            user_emotion = analyze_emotion_audio(state["audio_bytes"])

            state["transcript"] = transcript
            if not transcript or (isinstance(transcript, str) and not transcript.strip()):
                logger.error(
                    "❌ AudioIngestor produced EMPTY transcript for session %s after all fallbacks!",
                    state["session_id"],
                )
                transcript_preview = "EMPTY"
            else:
                transcript_preview = transcript[:50] if isinstance(transcript, str) else transcript
            state["user_emotion"] = EmotionData(
                label=user_emotion.label,
                confidence=user_emotion.confidence
            )

            logger.info(
                "AudioIngestor completed: transcript='%s...', emotion=%s(%.2f)",
                transcript_preview,
                user_emotion.label,
                user_emotion.confidence,
            )
            
        except Exception as e:
            logger.error(f"AudioIngestor failed: {e}")
            # Set fallback flag and try Whisper fallback
            state["fallback_used"]["stt"] = "whisper_fallback"
            state["transcript"] = self._whisper_fallback(state["audio_bytes"])
            logger.debug(
                "AudioIngestor: whisper fallback returned %s (len=%d)",
                repr(state["transcript"][:75] if isinstance(state["transcript"], str) else state["transcript"]),
                len(state["transcript"]) if isinstance(state["transcript"], str) else -1,
            )
            if not state["transcript"]:
                logger.warning(
                    "AudioIngestor whisper fallback produced empty transcript for session %s",
                    state["session_id"],
                )
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
        logger.debug(
            "IntentAnalyzer: received transcript %s (len=%d)",
            repr(transcript[:75] if isinstance(transcript, str) else transcript),
            len(transcript) if isinstance(transcript, str) else -1,
        )
        if not transcript:
            logger.warning(
                "IntentAnalyzer received empty transcript for session %s",
                state["session_id"],
            )

        # Simple rule-based intent classification
        intent = self._classify_intent(transcript)
        state["intent"] = intent

        logger.info(f"IntentAnalyzer completed: intent={intent}")
        return state
    
    def _classify_intent(self, text: str) -> str:
        """Enhanced intent classification - prioritizes DeFi keywords over emotional cues"""
        text_lower = text.lower()
        
        # Expanded DeFi keywords for better detection
        defi_keywords = [
            "defi", "yield", "staking", "liquidity", "farming", "token", 
            "swap", "protocol", "apy", "apr", "pool", "vault", "ethereum",
            "crypto", "blockchain", "smart contract", "wallet", "gas", "fee",
            "dex", "exchange", "collateral", "lending", "borrowing", "loan",
            "impermanent loss", "slippage", "tvl", "flash loan", "governance",
            "stablecoin", "usdc", "usdt", "dai", "mev", "risk", "audit"
        ]
        
        emotional_keywords = ["sad", "worried", "anxious", "happy", "excited", 
                             "confused", "frustrated", "help me"]
        
        # CRITICAL: DeFi keywords take priority over emotional keywords
        # This prevents "I'm confused about yield farming" from being classified as emotional_support
        if any(keyword in text_lower for keyword in defi_keywords):
            return "defi_question"
        elif any(keyword in text_lower for keyword in emotional_keywords):
            return "emotional_support"
        else:
            return "small_talk"

class ResponseGenerator:
    """Generates responses using Mistral LLM with context (emotion + memory + RAG)"""
    
    def __init__(self):
        self.settings = get_settings()
        logger.info("ResponseGenerator initialized (Mistral LLM)")
    
    def __call__(self, state: GraphState) -> GraphState:
        logger.info(f"ResponseGenerator processing session {state['session_id']}")
        state.setdefault("fallback_used", {})

        try:
            transcript = state.get("transcript", "")
            logger.debug(
                "ResponseGenerator: using transcript %s (len=%d)",
                repr(transcript[:75] if isinstance(transcript, str) else transcript),
                len(transcript) if isinstance(transcript, str) else -1,
            )
            if not transcript:
                logger.warning(
                    "ResponseGenerator received empty transcript for session %s",
                    state["session_id"],
                )
            # Build context from memory and state
            context = self._build_context(state)

            # Generate response with Mistral LLM
            response = self._generate_with_context(
                transcript,
                state.get("intent", ""),
                state["user_emotion"],
                context
            )
            state["llm_response"] = response
            
            logger.info(f"ResponseGenerator completed: response='{state['llm_response'][:50]}...'")
                
        except Exception as e:
            logger.error(f"ResponseGenerator failed: {e}")
            # Fallback to Claude-3
            state["fallback_used"]["llm"] = "claude_fallback"
            response = self._claude_fallback(state.get("transcript", ""), state.get("intent", ""))
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
        """Generate response with proper context separation (RAG in system message)"""
        # Get RAG context for DeFi questions
        rag_context = ""
        if intent == "defi_question":
            rag_context = rag_system.get_context_for_llm(transcript)
            logger.info(f"RAG context retrieved: {len(rag_context)} characters")
            if rag_context:
                logger.info(f"RAG context preview: {rag_context[:100]}...")
        
        # Use the new context-aware function instead of cramming everything into user message
        return generate_llm_reply_with_context(
            user_question=transcript,
            rag_context=rag_context,
            emotion_label=user_emotion.label,
            memory_context=context,
            intent=intent
        )
    
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
            logger.info(f"TTSNode: Calling Inworld TTS for text: '{state['llm_response'][:50]}...'")
            tts_bytes = synthesize_inworld(state["llm_response"])
            
            logger.info(f"TTSNode: Received {len(tts_bytes)} bytes from Inworld")
            
            # Check for mock audio
            is_mock = tts_bytes.startswith(b"ID3mock") or len(tts_bytes) < 100
            if is_mock:
                logger.warning("TTSNode: Received mock audio from Inworld (likely API key issue)")
                raise Exception("Mock audio received - triggering fallback")
            
            # Upload and get URL
            file_name = f"sophia_{int(time.time()*1000)}_{state['session_id']}.mp3"
            logger.info(f"TTSNode: Uploading to Supabase as {file_name}")
            
            audio_url = upload_audio_and_get_url(file_bytes=tts_bytes, file_name=file_name)
            
            logger.info(f"TTSNode: Successfully uploaded to {audio_url}")
            
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
            logger.error(f"❌ TTSNode Inworld failed: {type(e).__name__}: {str(e)}")
            
            # Log detailed error info
            import traceback
            logger.error(f"📋 TTSNode error traceback:\n{traceback.format_exc()}")
            
            # Fallback to OpenAI TTS
            state["fallback_used"]["tts"] = "openai_fallback"
            try:
                logger.info("TTSNode: Attempting OpenAI TTS fallback")
                tts_bytes = self._openai_tts_fallback(state["llm_response"])
                
                if not tts_bytes or len(tts_bytes) < 100:
                    raise Exception("OpenAI TTS returned no/invalid audio")
                
                file_name = f"sophia_fallback_{int(time.time()*1000)}_{state['session_id']}.mp3"
                logger.info(f"TTSNode fallback: Uploading OpenAI audio as {file_name}")
                
                audio_url = upload_audio_and_get_url(file_bytes=tts_bytes, file_name=file_name)
                sophia_emotion = analyze_emotion_audio(tts_bytes)
                
                state["tts_bytes"] = tts_bytes
                state["audio_url"] = audio_url
                state["sophia_emotion"] = EmotionData(
                    label=sophia_emotion.label,
                    confidence=sophia_emotion.confidence
                )
                logger.info(f"✅ TTSNode fallback succeeded: {audio_url}")
                
            except Exception as fallback_error:
                logger.error(f"❌ TTS fallback also failed: {type(fallback_error).__name__}: {str(fallback_error)}")
                logger.error(f"📋 Fallback error traceback:\n{traceback.format_exc()}")
                
                # Final fallback - empty audio but continue
                state["audio_url"] = ""
                state["sophia_emotion"] = EmotionData(label="neutral", confidence=0.5)
                logger.warning("⚠️ TTSNode: Using empty audio URL as final fallback")
        
        return state
    
    def _openai_tts_fallback(self, text: str) -> bytes:
        """Fallback TTS using OpenAI"""
        try:
            import openai
            settings = get_settings()
            
            if not settings.OPENAI_API_KEY:
                logger.error("OpenAI API key not configured")
                return b""
            
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",  # Changed from "alloy" for better female voice
                input=text,
                response_format="mp3"
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"OpenAI TTS fallback failed: {e}")
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
            "fallback_used": {},
            "use_voxtral_large": False  # Will be set by AudioIngestor
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
            "fallback_used": {},
            "use_voxtral_large": False  # Text-only uses legacy pipeline
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
    
    def process_audio_to_context(self, audio_bytes: bytes, session_id: Optional[str] = None) -> GraphState:
        """Process audio through initial nodes to get context for streaming"""
        
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
        
        # Process through initial nodes
        audio_ingestor = AudioIngestor()
        intent_analyzer = IntentAnalyzer()
        
        # Run audio processing and intent analysis
        state = audio_ingestor(initial_state)
        state = intent_analyzer(state)
        
        return state
    
    def stream_llm_response(self, state: GraphState):
        """Stream LLM response with context (emotion + memory + RAG)"""
        logger.info(f"Streaming LLM response for session {state['session_id']}")
        
        try:
            # Build context like ResponseGenerator does
            response_generator = ResponseGenerator()
            context = response_generator._build_context(state)
            
            # Get RAG context for DeFi questions
            rag_context = ""
            if state.get("intent") == "defi_question":
                rag_context = rag_system.get_context_for_llm(state.get("transcript", ""))
                logger.info(f"RAG context retrieved: {len(rag_context)} characters")
            
            # Build comprehensive prompt
            prompt_parts = [f"The user seems {state['user_emotion'].label} (confidence: {state['user_emotion'].confidence:.2f})."]
            
            if context:
                prompt_parts.append(f"Conversation context: {context}")
            
            if rag_context:
                prompt_parts.append(f"Relevant knowledge base:\n{rag_context}")
            
            prompt_parts.append(f"User question: {state.get('transcript', '')}")
            
            full_prompt = " | ".join(prompt_parts)
            
            # Stream response using Mistral LLM
            from app.services.mistral import stream_generate_llm_reply
            
            for token in stream_generate_llm_reply(full_prompt):
                yield token
                
        except Exception as e:
            logger.error(f"Streaming LLM response failed: {e}")
            # Final fallback
            if "defi" in state.get("transcript", "").lower() or "crypto" in state.get("transcript", "").lower():
                yield "I can help you with DeFi questions. What would you like to know?"
            else:
                yield "I'm here to help. Could you please rephrase your question?"
