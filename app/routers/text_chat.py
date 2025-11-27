"""
Enhanced Text Chat Router with SSE Meta Events

This replaces the basic /text-chat/stream endpoint with:
- Meta events: receiving → thinking → responding → resting
- Intent and routing info in meta events
- Cancellation support
- Unified session management with voice pipeline
"""

import asyncio
import logging
import time
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.deps import verify_api_key, limiter
from app.config import get_settings
from app.services.langgraph_service import langgraph_service
from app.langgraph_nodes import IntentAnalyzer, EmotionData
from app.services.memory import memory_manager, ConversationTurn
from app.services.tts import synthesize_inworld
from app.services.supabase import upload_audio_and_get_url, insert_conversation_session, insert_emotion_score
from app.services.evaluations import evaluation_manager
from app.services.mistral import generate_llm_reply_with_context
from app.services.rag import rag_system
from app.services.rate_limits import rate_limit_service
import json

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# In-memory cancellation flags (keyed by session_id)
_cancel_flags: Dict[str, bool] = {}


class TextChatRequest(BaseModel):
    """Request body for text chat"""
    message: str = Field(..., min_length=1, description="User's text message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    user_id: Optional[str] = Field(None, description="User ID for rate limiting")


class TextChatResponse(BaseModel):
    """Response for non-streaming text chat"""
    session_id: str
    transcript: str
    reply: str
    user_emotion: Dict[str, Any]
    sophia_emotion: Dict[str, Any]
    audio_url: str
    intent: str


def _check_cancelled(session_id: str) -> bool:
    """Check if session has been cancelled"""
    return _cancel_flags.get(session_id, False)


def _clear_cancel_flag(session_id: str):
    """Clear cancellation flag for session"""
    if session_id in _cancel_flags:
        del _cancel_flags[session_id]


async def _stream_text_chat_enhanced(message: str, session_id: Optional[str], user_id: str = None):
    """
    Enhanced streaming with SSE meta events for presence indicators.
    
    SSE Event Flow:
    1. meta (stage: receiving) - Request accepted
    2. meta (stage: thinking) - Analyzing intent + context
    3. meta (stage: responding) - Streaming LLM response
    4. token (text: "...") - Each token
    5. reply_done - Complete response with metadata
    6. audio_url - TTS audio (optional)
    7. meta (stage: resting) - Done
    """
    
    # Store original session_id to check if it's a follow-up
    original_session_id = session_id
    
    # Generate session_id if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Clear any existing cancel flag
    _clear_cancel_flag(session_id)
    
    try:
        # check rate limit
        from app.services.rate_limits import rate_limit_service
        
        limit_check = rate_limit_service.check_limits(
            user_id=user_id,
            additional_text_msgs=1
        )
        
        if not limit_check.allowed:
            # Send limit exceeded event
            error_data = json.dumps({
                "error": "USAGE_LIMIT_REACHED",
                "reason": limit_check.reason,
                "plan_tier": limit_check.plan_tier,
                "limit": limit_check.limit,
                "used": limit_check.used,
                "title": limit_check.title,
                "body": limit_check.body,
            })
            yield f"event: error\ndata: {error_data}\n\n"
            return 


        # EVENT 1: Receiving
        event_data = json.dumps({"stage": "receiving", "session_id": session_id})
        yield f"event: meta\ndata: {event_data}\n\n"
        
        if _check_cancelled(session_id):
            yield f"event: meta\ndata: {json.dumps({'stage': 'cancelled', 'session_id': session_id})}\n\n"
            return
        
        logger.info(f"[Text Chat Stream] Processing message for session {session_id}: '{message[:50]}...'")
        
        # EVENT 2: Thinking (analyze intent)
        intent_analyzer = IntentAnalyzer()
        temp_state = {
            "session_id": session_id,
            "transcript": message,
            "user_emotion": EmotionData(label="neutral", confidence=0.7),
            "intent": ""
        }
        
        state_with_intent = intent_analyzer(temp_state)
        intent = state_with_intent["intent"]
        
        # Get memory context
        context = memory_manager.get_context_for_llm(session_id)
        
        # Determine current_mode based on intent
        current_mode = "EMOTIONAL_SUPPORT" if intent == "emotional_support" else "UTILITY_DIRECT"
        
        event_data = json.dumps({
            "stage": "thinking",
            "session_id": session_id,
            "intent": intent,
            "current_mode": current_mode,
            "skill_id": None
        })
        yield f"event: meta\ndata: {event_data}\n\n"
        
        if _check_cancelled(session_id):
            yield f"event: meta\ndata: {json.dumps({'stage': 'cancelled', 'session_id': session_id})}\n\n"
            return
        
        # EVENT 3: Responding
        event_data = json.dumps({
            "stage": "responding",
            "session_id": session_id,
            "intent": intent
        })
        yield f"event: meta\ndata: {event_data}\n\n"
        
        # Get RAG context for DeFi questions
        rag_context = ""
        if intent == "defi_question":
            rag_context = rag_system.get_context_for_llm(message)
            logger.info(f"[Text Chat Stream] RAG context: {len(rag_context)} chars")
        
        # Generate LLM response
        full_response = generate_llm_reply_with_context(
            user_question=message,
            rag_context=rag_context,
            emotion_label="neutral",
            memory_context=str(context),
            intent=intent
        )
        
        # EVENT 4: Stream tokens (word by word for now)
        words = full_response.split()
        accumulated_response = ""
        
        for word in words:
            if _check_cancelled(session_id):
                yield f"event: meta\ndata: {json.dumps({'stage': 'cancelled', 'session_id': session_id})}\n\n"
                return
            
            token = word + " "
            accumulated_response += token
            
            # Safe JSON encoding
            token_data = json.dumps({"text": token})
            yield f"event: token\ndata: {token_data}\n\n"
            
            # Small delay to simulate streaming
            await asyncio.sleep(0.03)
        
        if _check_cancelled(session_id):
            yield f"event: meta\ndata: {json.dumps({'stage': 'cancelled', 'session_id': session_id})}\n\n"
            return
        
        # Generate TTS audio
        audio_url = ""
        sophia_emotion = EmotionData(label="neutral", confidence=0.5)
        tts_bytes = b""
        
        try:
            tts_bytes = synthesize_inworld(accumulated_response.strip())
            file_name = f"sophia_text_{int(time.time()*1000)}_{session_id}.mp3"
            audio_url = upload_audio_and_get_url(file_bytes=tts_bytes, file_name=file_name)
            
            from app.services.emotion import analyze_emotion_audio
            sophia_emotion = analyze_emotion_audio(tts_bytes)
            logger.info(f"[Text Chat Stream] TTS generated: {audio_url}")
        except Exception as e:
            logger.error(f"[Text Chat Stream] TTS failed: {e}")
        
        # EVENT 5: reply_done
        reply_data = json.dumps({
            "reply": accumulated_response.strip(),
            "session_id": session_id,
            "intent": intent,
            "current_mode": current_mode,
            "skill_id": None,
            "user_emotion": None,
            "sophia_emotion": {
                "label": sophia_emotion.label,
                "confidence": sophia_emotion.confidence
            }
        })
        yield f"event: reply_done\ndata: {reply_data}\n\n"
        
        # EVENT 6: audio_url (if generated)
        if audio_url:
            audio_data = json.dumps({
                "audio_url": audio_url,
                "sophia_emotion": {
                    "label": sophia_emotion.label,
                    "confidence": sophia_emotion.confidence
                },
                "mock_audio": False
            })
            yield f"event: audio_url\ndata: {audio_data}\n\n"
        
        # Save to database (with session validation like normal endpoint)
        try:
            # Check if session already exists in database
            from app.services.supabase import get_supabase, insert_conversation_message
            supabase = get_supabase()
            session_exists = False
            
            if original_session_id:  # User provided a session_id
                try:
                    result = supabase.table("conversation_sessions").select("id").eq("id", session_id).execute()
                    session_exists = bool(result.data)
                except Exception:
                    session_exists = False
            
            # Insert session ONLY if it's new
            if not session_exists:
                try:
                    session_data = {
                        "id": session_id,
                        "user_id": user_id or "00000000-0000-0000-0000-000000000000",
                        "transcript": message,
                        "response": accumulated_response.strip(),
                        "user_emotion": {
                            "label": "neutral",
                            "confidence": 0.7
                        },
                        "sophia_emotion": {
                            "label": sophia_emotion.label,
                            "confidence": sophia_emotion.confidence
                        },
                        "audio_url": audio_url,
                        "source": "web"
                    }
                    insert_conversation_session(session_data)
                    logger.info(f"[Text Chat Stream] ✅ New session created: {session_id}")
                except Exception as session_error:
                    logger.warning(f"[Text Chat Stream] ⚠️ Session insert failed (may already exist): {session_error}")
            else:
                logger.info(f"[Text Chat Stream] ✅ Continuing existing session: {session_id}")
            
            # ALWAYS insert messages (for multi-turn support)
            try:
                insert_conversation_message({
                    "session_id": session_id,
                    "role": "user",
                    "content": message,
                    "emotion": {
                        "label": "neutral",
                        "confidence": 0.7
                    }
                })
                logger.info(f"[Text Chat Stream] ✅ User message saved to conversation_messages")
            except Exception as msg_error:
                logger.error(f"[Text Chat Stream] ❌ Failed to save user message: {msg_error}")
            
            try:
                insert_conversation_message({
                    "session_id": session_id,
                    "role": "sophia",
                    "content": accumulated_response.strip(),
                    "audio_url": audio_url,
                    "emotion": {
                        "label": sophia_emotion.label,
                        "confidence": sophia_emotion.confidence
                    }
                })
                logger.info(f"[Text Chat Stream] ✅ Sophia message saved to conversation_messages")
            except Exception as msg_error:
                logger.error(f"[Text Chat Stream] ❌ Failed to save sophia message: {msg_error}")
            
            # Insert emotion scores
            try:
                insert_emotion_score(session_id, "user", EmotionData(label="neutral", confidence=0.7), user_id)
                insert_emotion_score(session_id, "sophia", sophia_emotion, user_id)
            except Exception as emotion_error:
                logger.warning(f"[Text Chat Stream] ⚠️ Failed to save emotion scores: {emotion_error}")
                
        except Exception as e:
            logger.error(f"[Text Chat Stream] ❌ Failed to save conversation: {e}")
        
        # Update memory
        conversation_turn = ConversationTurn(
            query=message,
            response=accumulated_response.strip(),
            user_emotion="neutral",
            sophia_emotion=sophia_emotion.label,
            intent=intent,
            timestamp=time.time()
        )
        memory_manager.update_session_memory(session_id, conversation_turn)
        
        # Collect evaluation data
        try:
            evaluation_manager.collect_message_data(
                session_id=session_id,
                query=message,
                answer=accumulated_response.strip(),
                user_audio=b"",
                sophia_audio=tts_bytes if audio_url else b"",
                retrieved_context=rag_context
            )
        except Exception as e:
            logger.error(f"[Text Chat Stream] Failed to collect evaluation data: {e}")

        try:
            rate_limit_service.add_text_usage(user_id, messages=1)
            logger.info(f"[Text Chat Stream] Usage incremented for user {user_id}")
        except Exception as e:
            logger.error(f"[Text Chat Stream] Failed to increment usage: {e}")
        
        # 💜 Track usage after successful processing (best effort)
        if user_id:
            try:
                logger.info(f"[Text Chat Stream] Attempting to track text usage for user {user_id}")
                rate_limit_service.add_text_usage(user_id=user_id, messages=1)
                logger.info(f"[Text Chat Stream] ✅ Successfully tracked text usage for user {user_id}")
            except Exception as e:
                logger.error(f"[Text Chat Stream] ❌ Failed to track text usage for user {user_id}: {e}", exc_info=True)
        
        # EVENT 7: Resting
        yield f"event: meta\ndata: {json.dumps({'stage': 'resting', 'session_id': session_id})}\n\n"
        
        _clear_cancel_flag(session_id)
        logger.info(f"[Text Chat Stream] Completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"[Text Chat Stream] Failed: {e}", exc_info=True)
        error_data = json.dumps({"detail": f"Internal server error: {str(e)}"})
        yield f"event: error\ndata: {error_data}\n\n"
        _clear_cancel_flag(session_id)

@router.post("/stream")
@limiter.limit(settings.API_RATE_LIMIT)
async def text_chat_stream_enhanced(
    request: Request,
    body: TextChatRequest,
    user_id: str = Query("00000000-0000-0000-0000-000000000000", description="User ID"),
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Enhanced streaming text chat with SSE meta events.
    
    **SSE Event Types:**
    - `meta`: Stage updates (receiving, thinking, responding, resting, cancelled)
    - `token`: Individual text tokens from LLM
    - `reply_done`: Complete response with metadata
    - `audio_url`: TTS audio URL
    - `error`: Error message
    
    **Headers:**
    - Authorization: Bearer <API_KEY>
    - Accept: text/event-stream
    """
    """Enhanced streaming text chat with rate limits."""
    
    logger.info(f"[Enhanced Text Chat] user_id={user_id}, message='{body.message[:50]}...'")
    
    return StreamingResponse(
        _stream_text_chat_enhanced(body.message, body.session_id, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{session_id}/cancel")
@limiter.limit(settings.API_RATE_LIMIT)
async def cancel_text_chat(
    request: Request,
    session_id: str,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Cancel an ongoing text chat stream.
    
    Sets a cancellation flag that the streaming generator checks periodically.
    """
    logger.info(f"[Text Chat Cancel] Cancellation requested for session {session_id}")
    _cancel_flags[session_id] = True
    return {"status": "cancellation_requested", "session_id": session_id}


@router.post("")
@limiter.limit(settings.API_RATE_LIMIT)
async def text_chat_non_streaming(
    request: Request,
    body: TextChatRequest,
    user_id: str = Query("00000000-0000-0000-0000-000000000000", description="User ID for rate limiting"),
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Non-streaming text chat endpoint with rate limiting.
    """
    
    logger.info(f"[Text Chat] user_id={user_id}, message='{body.message[:50]}...'")
    
    # CHECK RATE LIMITS BEFORE PROCESSING
    limit_check = rate_limit_service.check_limits(
        user_id=user_id,
        additional_text_msgs=1
    )
    
    if not limit_check.allowed:
        logger.warning(f"[Text Chat] Rate limit exceeded for user {user_id}: {limit_check.reason}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "USAGE_LIMIT_REACHED",
                "reason": limit_check.reason,
                "plan_tier": limit_check.plan_tier,
                "limit": limit_check.limit,
                "used": limit_check.used,
                "title": limit_check.title,
                "body": limit_check.body,
            }
        )
    
    # Process normally
    result = langgraph_service.process_text_conversation(
        message=body.message,
        session_id=body.session_id,
        collect_evaluation_data=True
    )
    
    # INCREMENT USAGE AFTER SUCCESSFUL PROCESSING
    try:
        rate_limit_service.add_text_usage(user_id, messages=1)
        logger.info(f"[Text Chat] Usage incremented for user {user_id}")
    except Exception as e:
        logger.error(f"[Text Chat] Failed to increment usage: {e}")
    
    return TextChatResponse(
        session_id=result["session_id"],
        transcript=result["transcript"],
        reply=result["reply"],
        user_emotion=result["user_emotion"],
        sophia_emotion=result["sophia_emotion"],
        audio_url=result["audio_url"],
        intent=result["intent"]
    )