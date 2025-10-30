"""Supabase client utilities for storage uploads, consent checks, and conversation inserts."""

import logging
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional
from dotenv import load_dotenv, find_dotenv
from supabase import Client, create_client

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.config import Settings, get_settings

# Load environment variables from .env (portable)
load_dotenv(find_dotenv(), override=False)

# Global Supabase client state
_supabase: Optional[Client] = None
SUPABASE_BUCKET_AUDIO: str = "audio"
SUPABASE_AUDIO_PREFIX: str = "uploads/"
SUPABASE_DB_DSN: Optional[str] = None
_DEFAULT_USER_ID: Optional[str] = None

ZERO_UUID = "00000000-0000-0000-0000-000000000000"

logger = logging.getLogger("sophia-backend")
_supabase_tracer = trace.get_tracer("sophia.supabase")

# Optional: direct SQL helpers if available
try:
    from app.services.db import insert_emotion_score_sql, insert_conversation_session_sql  # type: ignore
except Exception:
    insert_emotion_score_sql = None  # type: ignore
    insert_conversation_session_sql = None  # type: ignore


def _validate_uuid(value: str) -> Optional[str]:
    try:
        uuid.UUID(value)
        return value
    except Exception:
        logger.warning("Invalid UUID supplied for Supabase operations: %s", value)
        return None


def user_uuid_from_discord(discord_id: Optional[str]) -> Optional[str]:
    if not discord_id:
        return None
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, "https://sophia.ai/discord")
    return str(uuid.uuid5(namespace, discord_id.strip()))


def _default_user_id(settings: Optional[Settings] = None) -> str:
    """Return a reusable default user_id that is never the all-zero UUID."""

    global _DEFAULT_USER_ID
    if _DEFAULT_USER_ID:
        return _DEFAULT_USER_ID

    if settings is None:
        settings = get_settings()

    candidate = (settings.SUPABASE_DEFAULT_USER_ID or "").strip()
    if candidate == ZERO_UUID:
        logger.warning("Configured SUPABASE_DEFAULT_USER_ID is the zero UUID and will be ignored.")
        candidate = ""

    candidate = _validate_uuid(candidate) if candidate else None

    if not candidate:
        candidate = str(uuid.uuid4())
        logger.info("Generated fallback Supabase user_id %s for development flows.", candidate)

    _DEFAULT_USER_ID = candidate
    return _DEFAULT_USER_ID


def _resolve_user_id(user_id: Optional[str], discord_id: Optional[str] = None) -> str:
    candidate = (user_id or "").strip()
    if candidate == ZERO_UUID:
        logger.warning("Received zero UUID for user_id; substituting default user identifier.")
        candidate = ""
    candidate = _validate_uuid(candidate) if candidate else None
    if candidate:
        return candidate
    derived = user_uuid_from_discord(discord_id)
    if derived:
        return derived
    return _default_user_id()


@contextmanager
def _supabase_span(name: str, **attrs):
    with _supabase_tracer.start_as_current_span(name) as span:
        for key, value in attrs.items():
            if value is None:
                continue
            span.set_attribute(f"supabase.{key}", value)
        try:
            yield span
        except Exception as exc:  # pragma: no cover - instrumentation path
            span.record_exception(exc)
            span.set_status(Status(status_code=StatusCode.ERROR, description=str(exc)))
            raise


def init_supabase(settings: Optional[Settings] = None) -> Client:
    """Initialise the Supabase client once using application settings."""

    global _supabase, SUPABASE_BUCKET_AUDIO, SUPABASE_AUDIO_PREFIX, SUPABASE_DB_DSN
    if _supabase is not None:
        return _supabase

    if settings is None:
        settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError("Supabase credentials not configured; set SUPABASE_URL and SUPABASE_KEY")

    SUPABASE_BUCKET_AUDIO = settings.SUPABASE_BUCKET_AUDIO or "audio"
    SUPABASE_AUDIO_PREFIX = settings.SUPABASE_AUDIO_PREFIX or "uploads/"
    SUPABASE_DB_DSN = settings.SUPABASE_DB_DSN
    _default_user_id(settings)

    with _supabase_span("supabase.init"):
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase


def get_supabase() -> Client:
    """Return the shared Supabase client, initialising it if necessary."""

    if _supabase is not None:
        return _supabase
    return init_supabase()
    
def upload_audio_and_get_url(file_bytes: bytes, file_name: Optional[str] = None) -> str:
    """Upload audio file to Supabase storage and return public URL.
    
    Note: This function doesn't require a user_id as it uses storage, not the database.
    """
    if not file_name:
        file_name = f"sophia_{uuid.uuid4().hex}.mp3"
    path = f"{SUPABASE_AUDIO_PREFIX}{file_name}"

    client = get_supabase()

    with _supabase_span("supabase.audio.remove", path=path):
        try:
            client.storage.from_(SUPABASE_BUCKET_AUDIO).remove([path])
        except Exception:
            pass

    with _supabase_span("supabase.audio.upload", path=path, bucket=SUPABASE_BUCKET_AUDIO):
        try:
            client.storage.from_(SUPABASE_BUCKET_AUDIO).upload(path, file_bytes)
        except Exception as e:
            raise RuntimeError(f"Supabase upload failed: {e}")

    with _supabase_span("supabase.audio.public_url", path=path):
        public_url = client.storage.from_(SUPABASE_BUCKET_AUDIO).get_public_url(path)
    return public_url


def insert_emotion_score(
    session_id,
    role: str,
    emotion: Any,
    user_id: str = None,
    discord_id: Optional[str] = None,
) -> None:
    """Insert a row into the emotion_scores table using the test user ID if none provided.
    
    Note: This function will always use the test user ID if no user_id is provided.
    """
    resolved_user_id = _resolve_user_id(user_id, discord_id)

    payload = {
        "session_id": str(session_id),
        "role": role,
        "label": getattr(emotion, "label", "neutral"),
        "confidence": float(getattr(emotion, "confidence", 0.5)),
        "user_id": resolved_user_id,
    }
    
    client = get_supabase()

    try:
        with _supabase_span("supabase.insert_emotion_score", session_id=str(session_id), role=role):
            client.table("emotion_scores").insert(payload).execute()
    except Exception as e:
        import logging
        logging.warning(f"emotion_scores insert failed: {e}")
        # Don't raise the exception, just log it and continue
    if SUPABASE_DB_DSN and insert_emotion_score_sql:
        try:
            with _supabase_span("supabase.sql.insert_emotion_score", session_id=str(session_id), role=role):
                insert_emotion_score_sql(payload)
            return
        except Exception:
            pass


def insert_conversation_session(data: Dict[str, Any]) -> None:
    """Insert a conversation session row using SQL if DSN is set; otherwise REST.
    
    Note: This function will always use the test user ID if no user_id is provided.
    """
    discord_id = data.pop("discord_id", None)
    data["user_id"] = _resolve_user_id(data.get("user_id"), discord_id)

    # Ensure all SQL parameters expected by insert_conversation_session_sql are present
    # If missing, provide sensible defaults.
    # Required by SQL helper: id, user_id, transcript, reply,
    # user_emotion_label, user_emotion_confidence, sophia_emotion_label,
    # sophia_emotion_confidence, audio_url
    if "id" not in data or not data.get("id"):
        # Generate a session id if not provided
        data["id"] = str(uuid.uuid4())
    # Default optional fields to None if absent
    data.setdefault("transcript", None)
    data.setdefault("reply", None)
    data.setdefault("user_emotion_label", None)
    data.setdefault("user_emotion_confidence", None)
    data.setdefault("sophia_emotion_label", None)
    data.setdefault("sophia_emotion_confidence", None)
    data.setdefault("audio_url", None)
            
    client = get_supabase()

    if SUPABASE_DB_DSN and insert_conversation_session_sql:
        try:
            with _supabase_span("supabase.sql.insert_conversation", session_id=data.get("id")):
                insert_conversation_session_sql(data)
            return
        except Exception as e:
            import logging
            logging.warning(f"SQL insert_conversation_session failed: {e}")

    # REST insert with clearer error surfacing
    try:
        with _supabase_span("supabase.insert_conversation", session_id=data.get("id")):
            client.table("conversation_sessions").insert(data).execute()
    except Exception as e:
        # Log error but don't raise exception
        import logging
        logging.warning(f"conversation_sessions insert failed: {e}")
        # Don't raise the exception, just log it and continue


def has_user_consent(discord_id: str) -> bool:
    """Check if a given Discord user has a consent record in Supabase.
    
    Table schema expected: user_consents(discord_id text, consent_hash text, timestamp timestamptz, ip_address text)
    """
    try:
        client = get_supabase()
        with _supabase_span("supabase.get_user_consent"):
            res = client.table("user_consents").select("discord_id").eq("discord_id", discord_id).limit(1).execute()
        return bool(getattr(res, "data", []) or [])
    except Exception as e:
        import logging
        logging.warning(f"has_user_consent lookup failed: {e}")
        return False


def save_user_consent(discord_id: str, consent_hash: str, timestamp_iso: str, ip: Optional[str] = None) -> bool:
    """Persist a consent record. Returns True if stored.
    """
    try:
        payload = {
            "discord_id": discord_id,
            "consent_hash": consent_hash,
            "timestamp": timestamp_iso,
            "ip_address": ip or "",
        }
        client = get_supabase()
        with _supabase_span("supabase.insert_user_consent"):
            client.table("user_consents").insert(payload).execute()
        return True
    except Exception as e:
        import logging
        logging.warning(f"save_user_consent failed: {e}")
        return False
