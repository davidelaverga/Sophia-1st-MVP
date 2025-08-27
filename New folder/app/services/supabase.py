import time
from typing import Any, Dict
from supabase import create_client, Client
from app.config import get_settings

# Optional direct Postgres helpers (transaction pooler)
try:
    from app.services.db import insert_emotion_score_sql, insert_conversation_session_sql  # type: ignore
except Exception:  # pragma: no cover
    insert_emotion_score_sql = None  # type: ignore
    insert_conversation_session_sql = None  # type: ignore

_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        settings = get_settings()
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError("Supabase credentials not configured")
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase


def upload_audio_and_get_url(file_name: str, content: bytes) -> str:
    sb = get_supabase()
    settings = get_settings()
    path = f"{settings.SUPABASE_AUDIO_PREFIX}{file_name}"
    bucket = settings.SUPABASE_BUCKET_AUDIO
    # Upload file; allow upsert to avoid collisions during tests
    sb.storage.from_(bucket).upload(
        path,
        content,
        {
            "contentType": "audio/mpeg",
            "upsert": True,
        },
    )
    # Return public URL
    public_url = sb.storage.from_(bucket).get_public_url(path)
    return public_url


def insert_emotion_score(session_id, role: str, emotion) -> None:
    """Insert a row into emotion_scores table using SQL if DSN is set; otherwise REST."""
    settings = get_settings()
    payload = {
        "session_id": str(session_id),
        "role": role,
        "label": getattr(emotion, "label", "neutral"),
        "confidence": float(getattr(emotion, "confidence", 0.5)),
        "timestamp": int(time.time()),
    }
    # Prefer direct SQL via transaction pooler
    if getattr(settings, "SUPABASE_DB_DSN", None) and insert_emotion_score_sql:
        try:
            insert_emotion_score_sql(payload)
            return
        except Exception:
            # Fallback to REST if SQL path fails
            pass
    # REST fallback
    sb = get_supabase()
    sb.table("emotion_scores").insert(payload).execute()


def insert_conversation_session(data: Dict[str, Any]) -> None:
    """Insert a conversation session row using SQL if DSN is set; otherwise REST."""
    settings = get_settings()
    if getattr(settings, "SUPABASE_DB_DSN", None) and insert_conversation_session_sql:
        try:
            insert_conversation_session_sql(data)
            return
        except Exception:
            pass
    sb = get_supabase()
    sb.table("conversation_sessions").insert(data).execute()
