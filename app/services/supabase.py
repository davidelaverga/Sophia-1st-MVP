"""Supabase client utilities for storage uploads, consent checks, and conversation inserts."""

import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv, find_dotenv
except ImportError:  # pragma: no cover - optional dependency for local dev

    def load_dotenv(*_args, **_kwargs):  # type: ignore[override]
        return False

    def find_dotenv(*_args, **_kwargs):  # type: ignore[override]
        return ""


from supabase import Client, create_client

try:
    from supabase import ClientOptions  # type: ignore
except (
    ImportError
):  # pragma: no cover - for environments without recent supabase package
    ClientOptions = None  # type: ignore

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.config import Settings, get_settings

# Load environment variables from .env (portable)
load_dotenv(find_dotenv(), override=False)

# Global Supabase client state
_supabase: Optional[Client] = None
_anon_supabase: Optional[Client] = None
SUPABASE_BUCKET_AUDIO = os.getenv("SUPABASE_BUCKET_AUDIO", "audio-uploads")
SUPABASE_AUDIO_PREFIX = os.getenv("SUPABASE_AUDIO_PREFIX", "uploads/")
SUPABASE_SIGNED_URL_TTL = os.getenv("SUPABASE_SIGNED_URL_TTL", 3600)
SUPABASE_DB_DSN = os.getenv("SUPABASE_DB_DSN", None)

logger = logging.getLogger("sophia-backend")
_supabase_tracer = trace.get_tracer("sophia.supabase")


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

    global \
        _supabase, \
        _anon_supabase, \
        SUPABASE_BUCKET_AUDIO, \
        SUPABASE_AUDIO_PREFIX, \
        SUPABASE_DB_DSN, \
        SUPABASE_SIGNED_URL_TTL
    if _supabase is not None:
        return _supabase

    if settings is None:
        settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError(
            "Supabase credentials not configured; set SUPABASE_URL and SUPABASE_KEY"
        )

    anon_key = settings.SUPABASE_ANON_KEY or settings.SUPABASE_KEY
    if not anon_key:
        raise RuntimeError(
            "Supabase anon credentials not configured; set SUPABASE_ANON_KEY or SUPABASE_KEY"
        )
    if not settings.SUPABASE_ANON_KEY:
        logger.info(
            "SUPABASE_ANON_KEY not configured; using SUPABASE_KEY for anon client"
        )

    SUPABASE_BUCKET_AUDIO = settings.SUPABASE_BUCKET_AUDIO or "audio"
    SUPABASE_AUDIO_PREFIX = settings.SUPABASE_AUDIO_PREFIX or "uploads/"
    SUPABASE_SIGNED_URL_TTL = max(
        1, int(getattr(settings, "SUPABASE_SIGNED_URL_TTL", 3600))
    )
    SUPABASE_DB_DSN = settings.SUPABASE_DB_DSN

    with _supabase_span("supabase.init"):
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        options = None
        if ClientOptions is not None:
            options = ClientOptions(persist_session=False)  # type: ignore[arg-type]
        _anon_supabase = create_client(settings.SUPABASE_URL, anon_key, options=options)
    return _supabase


def _service_supabase() -> Client:
    if _supabase is not None:
        return _supabase
    return init_supabase()


def _client_with_access_token(access_token: str) -> Client:
    settings = get_settings()
    global _anon_supabase
    if _anon_supabase is None:
        init_supabase(settings)
    if _anon_supabase is None:
        raise RuntimeError("Supabase anon client failed to initialize")

    try:
        _anon_supabase.auth.set_session(access_token, "")
    except AttributeError:
        # Fallback for older SDKs without auth helper
        postgrest_client = getattr(_anon_supabase, "postgrest", None)
        if postgrest_client is None:
            raise RuntimeError(
                "Supabase client is missing postgrest interface required for RLS queries."
            )
        session = getattr(postgrest_client, "session", None)
        headers = getattr(session, "headers", None)
        if headers is None:
            raise RuntimeError(
                "Supabase postgrest client session has no headers object."
            )
        headers["Authorization"] = f"Bearer {access_token}"

    return _anon_supabase


def get_supabase(access_token: Optional[str] = None) -> Client:
    """Return a Supabase client. If `access_token` is provided, scope the client to that user."""

    if not access_token:
        return _service_supabase()
    return _client_with_access_token(access_token)


def upload_audio_and_get_url(file_bytes: bytes, file_name: Optional[str] = None) -> str:
    """Upload audio file to Supabase storage and return a signed URL.

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

    with _supabase_span(
        "supabase.audio.upload", path=path, bucket=SUPABASE_BUCKET_AUDIO
    ):
        try:
            client.storage.from_(SUPABASE_BUCKET_AUDIO).upload(path, file_bytes)
        except Exception as e:
            raise RuntimeError(f"Supabase upload failed: {e}")

    with _supabase_span(
        "supabase.audio.signed_url",
        path=path,
        expires_in=SUPABASE_SIGNED_URL_TTL,
    ):
        try:
            signed = client.storage.from_(SUPABASE_BUCKET_AUDIO).create_signed_url(
                path,
                SUPABASE_SIGNED_URL_TTL,
            )
        except Exception as e:
            raise RuntimeError(f"Supabase signed URL generation failed: {e}")

    signed_url = None
    if isinstance(signed, dict):
        signed_url = signed.get("signedURL") or signed.get("signed_url")
    if not signed_url:
        raise RuntimeError("Supabase signed URL generation returned no URL")

    # Supabase returns a relative path; prepend the base URL when needed.
    if signed_url.startswith("http://") or signed_url.startswith("https://"):
        return signed_url

    settings = get_settings()
    base_url = (settings.SUPABASE_URL or "").rstrip("/")
    if base_url:
        return f"{base_url}{signed_url}"
    # As a last resort return the relative URL so the caller can handle it.
    return signed_url


def insert_emotion_score(
    session_id,
    role: str,
    emotion: Any,
    user_id: str,
    access_token: Optional[str] = None,
) -> None:
    """Insert a row into the emotion_scores table"""

    payload = {
        "session_id": str(session_id),
        "role": role,
        "label": getattr(emotion, "label", "neutral"),
        "confidence": float(getattr(emotion, "confidence", 0.5)),
        "user_id": user_id,
    }

    client = get_supabase(access_token)

    try:
        with _supabase_span(
            "supabase.insert_emotion_score", session_id=str(session_id), role=role
        ):
            client.table("emotion_scores").insert(payload).execute()
    except Exception as e:
        import logging

        logging.warning(f"emotion_scores insert failed: {e}")
        # Don't raise the exception, just log it and continue


def persist_session_memory(
    memory_record: Dict[str, Any], access_token: Optional[str] = None
) -> None:
    """Upsert a session-level memory summary into session_memory."""
    session_id = memory_record.get("session_id")
    if not session_id:
        logger.warning("session_memory upsert skipped: missing session_id")
        return

    payload = {
        "session_id": str(session_id),
        "topics": memory_record.get("topics") or [],
        "turn_count": int(memory_record.get("turn_count", 0)),
        "last_user_emotion": memory_record.get("last_user_emotion") or "neutral",
        "last_sophia_emotion": memory_record.get("last_sophia_emotion") or "neutral",
    }

    try:
        client = get_supabase(access_token)
    except Exception as exc:
        logger.warning("session_memory upsert skipped (client init failed): %s", exc)
        return

    try:
        with _supabase_span("supabase.persist_session_memory", session_id=str(session_id)):
            client.table("session_memory").upsert(
                payload, on_conflict="session_id"
            ).execute()
    except Exception as exc:
        logger.warning("session_memory upsert failed: %s", exc)


def insert_conversation_session(
    data: Dict[str, Any], access_token: Optional[str] = None
) -> None:
    """Insert a conversation session row using REST."""

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

    client = get_supabase(access_token)

    # REST insert with clearer error surfacing
    try:
        with _supabase_span("supabase.insert_conversation", session_id=data.get("id")):
            client.table("conversation_sessions").insert(data).execute()
    except Exception as e:
        # Log error but don't raise exception
        import logging

        logging.warning(f"conversation_sessions insert failed: {e}")
        # Don't raise the exception, just log it and continue


def persist_conversation_turn(
    session_id: Optional[str],
    user_id: Optional[str],
    messages: List[Dict[str, Any]],
    session_metadata: Optional[Dict[str, Any]] = None,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Ensure a session exists and append one or more messages to it.

    Args:
        session_id: Conversation session UUID (generated if missing).
        user_id: Owning user UUID for RLS. Optional for service-role writes.
        messages: List of message payloads with at least `role` and either
                  `content` or `transcript`. Optional fields match the
                  conversation_messages schema.
        session_metadata: Optional session-level fields to upsert
                          (status, last_intent, last_*_emotion, title, context_summary).
        access_token: User-scoped token to satisfy RLS.

    Returns:
        Dict containing the session_id used and any inserted message_ids.
    """

    if not messages:
        return {"session_id": session_id, "message_ids": []}

    session_uuid = str(session_id or uuid.uuid4())
    client = get_supabase(access_token)

    # Build session payload; rely on DB defaults for started_at/turn_count.
    session_payload: Dict[str, Any] = {"id": session_uuid, "last_activity_at": datetime.utcnow().isoformat()}
    if user_id:
        session_payload["user_id"] = user_id
    if session_metadata:
        allowed_fields = {
            "status",
            "last_intent",
            "last_user_emotion_label",
            "last_user_emotion_confidence",
            "last_sophia_emotion_label",
            "last_sophia_emotion_confidence",
            "title",
            "context_summary",
            "turn_count",
            "ended_at",
        }
        for key, value in session_metadata.items():
            if key in allowed_fields:
                session_payload[key] = value

    try:
        with _supabase_span("supabase.upsert_session", session_id=session_uuid):
            client.table("conversation_sessions").upsert(
                session_payload, on_conflict="id"
            ).execute()
    except Exception as exc:
        logging.warning("conversation_sessions upsert failed: %s", exc)

    # Determine the starting turn index when not provided.
    next_turn_index = 0
    try:
        result = (
            client.table("conversation_messages")
            .select("turn_index")
            .eq("session_id", session_uuid)
            .order("turn_index", desc=True)
            .limit(1)
            .execute()
        )
        last_row = (getattr(result, "data", None) or [])
        if last_row:
            next_turn_index = int(last_row[0].get("turn_index", -1)) + 1
    except Exception as exc:
        logging.warning("conversation_messages turn_index lookup failed: %s", exc)

    message_rows: List[Dict[str, Any]] = []
    for offset, msg in enumerate(messages):
        turn_index = msg.get("turn_index")
        if turn_index is None:
            turn_index = next_turn_index + offset

        payload = {
            "session_id": session_uuid,
            "turn_index": turn_index,
            "role": msg.get("role"),
            "content": msg.get("content"),
            "transcript": msg.get("transcript"),
            "audio_url": msg.get("audio_url"),
            "intent": msg.get("intent"),
            "input_type": msg.get("input_type"),
            "emotion_label": msg.get("emotion_label"),
            "emotion_confidence": msg.get("emotion_confidence"),
            "token_count": msg.get("token_count"),
            "latency_ms": msg.get("latency_ms"),
        }
        message_rows.append(payload)

    message_ids: List[str] = []
    inserted_rows: List[Dict[str, Any]] = []
    try:
        with _supabase_span(
            "supabase.insert_conversation_messages",
            session_id=session_uuid,
            message_count=len(message_rows),
        ):
            insert_result = (
                client.table("conversation_messages").insert(message_rows).execute()
            )
            inserted_rows = getattr(insert_result, "data", None) or []
            for row in inserted_rows:
                row_id = row.get("id")
                if row_id:
                    message_ids.append(str(row_id))
    except Exception as exc:
        logging.warning("conversation_messages insert failed: %s", exc)

    # Opportunistically insert emotion_scores per message
    try:
        emotion_rows: List[Dict[str, Any]] = []
        if inserted_rows and len(inserted_rows) == len(messages):
            for msg, row in zip(messages, inserted_rows):
                role = msg.get("role")
                if not role:
                    continue
                message_id = row.get("id")
                if not message_id:
                    continue
                label = msg.get("emotion_label")
                confidence = msg.get("emotion_confidence")
                if label is None or confidence is None:
                    continue
                emotion_rows.append(
                    {
                        "session_id": session_uuid,
                        "message_id": message_id,
                        "role": role,
                        "label": label,
                        "confidence": float(confidence),
                        "user_id": user_id,
                    }
                )
        if emotion_rows:
            with _supabase_span(
                "supabase.insert_emotion_scores",
                session_id=session_uuid,
                count=len(emotion_rows),
            ):
                client.table("emotion_scores").insert(emotion_rows).execute()
    except Exception as exc:
        logging.warning("emotion_scores insert failed: %s", exc)

    return {"session_id": session_uuid, "message_ids": message_ids}


def has_user_consent(discord_id: str, access_token: Optional[str] = None) -> bool:
    """Check if a given Discord user has a consent record in Supabase.

    Table schema expected: user_consents(discord_id text, consent_hash text, timestamp timestamptz, ip_address text)
    """
    try:
        client = get_supabase(access_token)
        with _supabase_span("supabase.get_user_consent"):
            res = (
                client.table("user_consents")
                .select("discord_id")
                .eq("discord_id", discord_id)
                .limit(1)
                .execute()
            )
        return bool(getattr(res, "data", []) or [])
    except Exception as e:
        import logging

        logging.warning(f"has_user_consent lookup failed: {e}")
        payload = getattr(e, "args", [None])[0]
        if isinstance(payload, dict) and payload.get("code") == "PGRST205":
            logging.info(
                "user_consents table missing; bypassing consent requirement for this environment."
            )
            return True
        return False


def save_user_consent(
    discord_id: str,
    consent_hash: str,
    timestamp_iso: str,
    ip: Optional[str] = None,
    access_token: Optional[str] = None,
) -> bool:
    """Persist a consent record. Returns True if stored."""
    try:
        payload = {
            "discord_id": discord_id,
            "consent_hash": consent_hash,
            "timestamp": timestamp_iso,
            "ip_address": ip or "",
        }
        client = get_supabase(access_token)
        with _supabase_span("supabase.insert_user_consent"):
            client.table("user_consents").insert(payload).execute()
        return True
    except Exception as e:
        import logging

        logging.warning(f"save_user_consent failed: {e}")
        return False
