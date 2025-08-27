import os
import time
import uuid
from typing import Any, Dict
from dotenv import load_dotenv
from supabase import create_client, Client

# Global client instance
_supabase: Client = None

# Load environment variables from .env
load_dotenv(r"C:\Users\ajdee\Sophia-1st-MVP (2)\Sophia-1st-MVP\.env")

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET_AUDIO = os.getenv("SUPABASE_BUCKET_AUDIO", "audio")
SUPABASE_AUDIO_PREFIX = os.getenv("SUPABASE_AUDIO_PREFIX", "uploads/")
SUPABASE_DB_DSN = os.getenv("SUPABASE_DB_DSN", None)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials not configured in .env")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Optional: direct SQL helpers if available
try:
    from app.services.db import insert_emotion_score_sql, insert_conversation_session_sql  # type: ignore
except Exception:
    insert_emotion_score_sql = None  # type: ignore
    insert_conversation_session_sql = None  # type: ignore

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        # Use environment variables directly for testing
        if not SUPABASE_URL or not SUPABASE_KEY:
            # Return the already-initialized client for testing
            return supabase
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase
    
def upload_audio_and_get_url(file_bytes: bytes, file_name: str = None) -> str:
    """Upload audio file to Supabase storage and return public URL.
    
    Note: This function doesn't require a user_id as it uses storage, not the database.
    """
    if not file_name:
        file_name = f"sophia_{uuid.uuid4().hex}.mp3"
    path = f"{SUPABASE_AUDIO_PREFIX}{file_name}"

    # Remove file if it exists
    try:
        supabase.storage.from_(SUPABASE_BUCKET_AUDIO).remove([path])
    except Exception:
        pass

    # Upload file (storage3 returns an UploadResponse object; exceptions indicate failures)
    try:
        res = supabase.storage.from_(SUPABASE_BUCKET_AUDIO).upload(path, file_bytes)
    except Exception as e:
        raise RuntimeError(f"Supabase upload failed: {e}")

    # Return public URL
    public_url = supabase.storage.from_(SUPABASE_BUCKET_AUDIO).get_public_url(path)
    return public_url


def insert_emotion_score(session_id, role: str, emotion: Any, user_id: str = None) -> None:
    """Insert a row into the emotion_scores table using the test user ID if none provided.
    
    Note: This function will always use the test user ID if no user_id is provided.
    """
    # Always use the test user ID if none provided
    if not user_id:
        # Use hardcoded test user ID
        user_id = "00000000-0000-0000-0000-000000000000"  # Test user ID
        import logging
        logging.info(f"Using test user ID for emotion score: {user_id}")
        
    # If we still don't have a user_id (which shouldn't happen), log and return
    if not user_id:
        import logging
        logging.warning("Skipping emotion score insertion: No valid user_id available")
        return
    
    payload = {
        "session_id": str(session_id),
        "role": role,
        "label": getattr(emotion, "label", "neutral"),
        "confidence": float(getattr(emotion, "confidence", 0.5)),
        "user_id": user_id,
    }
    
    try:
        supabase.table("emotion_scores").insert(payload).execute()
    except Exception as e:
        import logging
        logging.warning(f"emotion_scores insert failed: {e}")
        # Don't raise the exception, just log it and continue
    if SUPABASE_DB_DSN and insert_emotion_score_sql:
        try:
            insert_emotion_score_sql(payload)
            return
        except Exception:
            pass


def insert_conversation_session(data: Dict[str, Any]) -> None:
    """Insert a conversation session row using SQL if DSN is set; otherwise REST.
    
    Note: This function will always use the test user ID if no user_id is provided.
    """
    # Always use the test user ID if none provided
    if "user_id" not in data or not data["user_id"]:
        # Use hardcoded test user ID
        data["user_id"] = "00000000-0000-0000-0000-000000000000"  # Test user ID
        import logging
        logging.info(f"Using test user ID for conversation session: {data['user_id']}")
        
    # If we still don't have a user_id (which shouldn't happen), log a warning
    if "user_id" not in data or not data["user_id"]:
        import logging
        logging.warning("No valid user_id available for conversation_session")
        # We'll continue anyway and let the database handle any constraints
            
    if SUPABASE_DB_DSN and insert_conversation_session_sql:
        try:
            insert_conversation_session_sql(data)
            return
        except Exception as e:
            import logging
            logging.warning(f"SQL insert_conversation_session failed: {e}")

    # REST insert with clearer error surfacing
    try:
        supabase.table("conversation_sessions").insert(data).execute()
    except Exception as e:
        # Log error but don't raise exception
        import logging
        logging.warning(f"conversation_sessions insert failed: {e}")
        # Don't raise the exception, just log it and continue
