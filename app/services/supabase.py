import logging
import os
import time
import uuid
from typing import Any, Dict, Optional
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client

# CRITICAL: Load .env FIRST before importing config
load_dotenv(find_dotenv(), override=False)

logger = logging.getLogger(__name__)

# Global client instance
_supabase: Optional[Client] = None

# Get credentials directly from env (before config import to avoid circular dependency)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET_AUDIO = os.getenv("SUPABASE_BUCKET_AUDIO", "audio-uploads")
SUPABASE_AUDIO_PREFIX = os.getenv("SUPABASE_AUDIO_PREFIX", "uploads/")
SUPABASE_DB_DSN = os.getenv("SUPABASE_DB_DSN")

# Log credentials (masked for security)
logger.info(f"Supabase URL: {SUPABASE_URL}")
logger.info(f"Supabase KEY: {SUPABASE_KEY[:20] if SUPABASE_KEY else 'NOT SET'}...")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("❌ SUPABASE_URL or SUPABASE_KEY not configured in environment")
    raise RuntimeError("Supabase credentials not configured in environment")

# Initialize Supabase client ONCE
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Supabase client: {e}")
    raise


# Optional: direct SQL helpers if available
try:
    from app.services.db import insert_emotion_score_sql, insert_conversation_session_sql  # type: ignore
except Exception:
    insert_emotion_score_sql = None  # type: ignore
    insert_conversation_session_sql = None  # type: ignore


def get_supabase() -> Client:
    """Get the global Supabase client instance"""
    global _supabase
    if _supabase is None:
        _supabase = supabase
    return _supabase
    

def upload_audio_and_get_url(file_bytes: bytes, file_name: Optional[str] = None) -> str:
    """Upload audio file to Supabase storage and return public URL.
    
    Note: This function doesn't require a user_id as it uses storage, not the database.
    """
    if not file_name:
        file_name = f"sophia_{uuid.uuid4().hex}.mp3"
    path = f"{SUPABASE_AUDIO_PREFIX}{file_name}"

    # Remove file if it exists (optional - cleanup)
    try:
        supabase.storage.from_(SUPABASE_BUCKET_AUDIO).remove([path])
    except Exception:
        pass  # Ignore if file doesn't exist

    # Upload file
    try:
        supabase.storage.from_(SUPABASE_BUCKET_AUDIO).upload(path, file_bytes)
        public_url = supabase.storage.from_(SUPABASE_BUCKET_AUDIO).get_public_url(path)
        logger.info(f"✅ Audio uploaded: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"❌ Supabase upload failed: {e}")

        error_str = str(e).lower()
        if "503" in error_str or "service unavailable" in error_str or "dns" in error_str:
            logger.warning("⚠️ Supabase is experiencing an outage (503). Returning placeholder URL.")
            return f"https://placeholder.supabase.co/audio-uploads/{path}"

        # Return empty string instead of raising to avoid breaking the pipeline
        logger.warning("⚠️ Returning empty audio_url due to upload failure")
        return ""


def insert_emotion_score(session_id, role: str, emotion: Any, user_id: str = None) -> None:
    """Insert a row into the emotion_scores table using the test user ID if none provided.
    
    Note: This function will always use the test user ID if no user_id is provided.
    Table expects session_id as UUID.
    """
    # Always use the test user ID if none provided
    if not user_id:
        user_id = "00000000-0000-0000-0000-000000000000"  # Test user ID
        logger.debug(f"Using test user ID for emotion score: {user_id}")
        
    # Ensure session_id is UUID string format
    import uuid as uuid_module
    if isinstance(session_id, uuid_module.UUID):
        session_id_str = str(session_id)
    else:
        session_id_str = str(session_id)
    
    payload = {
        "session_id": session_id_str,  # Supabase will convert to UUID
        "role": role,
        "label": getattr(emotion, "label", "neutral"),
        "confidence": float(getattr(emotion, "confidence", 0.5)),
    }
    
    # Note: emotion_scores table doesn't have user_id column
    # Only conversation_sessions has user_id
    
    try:
        result = supabase.table("emotion_scores").insert(payload).execute()
        logger.debug(f"✅ Emotion score inserted: {session_id_str} - {role}")
    except Exception as e:
        logger.warning(f"⚠️ emotion_scores insert failed: {e}")
        logger.warning(f"   Payload: {payload}")
        # Don't raise the exception, just log it and continue
        
    # Try SQL helper if available
    if SUPABASE_DB_DSN and insert_emotion_score_sql:
        try:
            insert_emotion_score_sql(payload)
        except Exception:
            pass


def insert_conversation_session(data: Dict[str, Any]) -> None:
    """Insert a conversation session row.
    
    IMPORTANT: Matches actual database schema with JSONB emotion fields
    
    Database schema:
    - id (uuid)
    - user_id (text)
    - transcript (text)
    - response (text)
    - audio_url (text)
    - response_audio_url (text)
    - user_emotion (jsonb) - NOT separate label/confidence fields
    - sophia_emotion (jsonb) - NOT separate label/confidence fields
    - source (text)
    - latency (double precision)
    - timestamp (timestamptz)
    - created_at (timestamptz)
    """
    # Always use the test user ID if none provided
    if "user_id" not in data or not data["user_id"]:
        data["user_id"] = "00000000-0000-0000-0000-000000000000"  # Test user ID
        logger.debug(f"Using test user ID for conversation session: {data['user_id']}")
    
    # Ensure ID exists
    if "id" not in data or not data.get("id"):
        data["id"] = str(uuid.uuid4())
    
    # Build payload matching actual database schema
    payload = {
        "id": data["id"],
        "user_id": data["user_id"],
        "transcript": data.get("transcript"),
        "response": data.get("response"),
        "audio_url": data.get("audio_url"),
        "response_audio_url": data.get("response_audio_url"),
        "source": data.get("source", "web"),
        "latency": data.get("latency"),
    }
    
    # Convert emotion fields from separate label/confidence to JSONB
    # Handle user_emotion
    if "user_emotion" in data and isinstance(data["user_emotion"], dict):
        # Already in correct format (JSONB)
        payload["user_emotion"] = data["user_emotion"]
    elif "user_emotion_label" in data and "user_emotion_confidence" in data:
        # Convert from separate fields to JSONB
        payload["user_emotion"] = {
            "label": data["user_emotion_label"],
            "confidence": data["user_emotion_confidence"]
        }
    
    # Handle sophia_emotion
    if "sophia_emotion" in data and isinstance(data["sophia_emotion"], dict):
        # Already in correct format (JSONB)
        payload["sophia_emotion"] = data["sophia_emotion"]
    elif "sophia_emotion_label" in data and "sophia_emotion_confidence" in data:
        # Convert from separate fields to JSONB
        payload["sophia_emotion"] = {
            "label": data["sophia_emotion_label"],
            "confidence": data["sophia_emotion_confidence"]
        }
    
    # Remove None values to let database defaults handle them
    payload = {k: v for k, v in payload.items() if v is not None}
    
    # Try SQL helper first if available
    if SUPABASE_DB_DSN and insert_conversation_session_sql:
        try:
            insert_conversation_session_sql(payload)
            logger.info(f"✅ Conversation session inserted (SQL): {payload['id']}")
            return
        except Exception as e:
            logger.warning(f"⚠️ SQL insert_conversation_session failed: {e}")

    # REST insert fallback
    try:
        result = supabase.table("conversation_sessions").insert(payload).execute()
        logger.info(f"✅ Conversation session inserted (REST): {payload['id']}")
    except Exception as e:
        logger.error(f"❌ conversation_sessions insert failed: {e}")
        logger.error(f"   Payload attempted: {payload}")
        # Don't raise the exception, just log it and continue


def has_user_consent(discord_id: str) -> bool:
    """Check if a given Discord user has a consent record in Supabase.
    
    Table schema expected: user_consents(discord_id text, consent_hash text, timestamp timestamptz, ip text)
    """
    try:
        res = supabase.table("user_consents").select("discord_id").eq("discord_id", discord_id).limit(1).execute()
        return bool(getattr(res, "data", []) or [])
    except Exception as e:
        logger.warning(f"has_user_consent lookup failed: {e}")
        return False


def save_user_consent(discord_id: str, consent_hash: str, timestamp_iso: str, ip: Optional[str] = None) -> bool:
    """Persist a consent record. Returns True if stored.
    """
    try:
        payload = {
            "discord_id": discord_id,
            "consent_hash": consent_hash,
            "timestamp": timestamp_iso,
            "ip": ip or "",
        }
        supabase.table("user_consents").insert(payload).execute()
        logger.info(f"✅ User consent saved: {discord_id}")
        return True
    except Exception as e:
        logger.warning(f"save_user_consent failed: {e}")
        return False