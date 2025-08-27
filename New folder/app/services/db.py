import contextlib
from typing import Any, Dict
import psycopg

from app.config import get_settings


def _get_conn():
    settings = get_settings()
    if not settings.SUPABASE_DB_DSN:
        raise RuntimeError("SUPABASE_DB_DSN not configured")
    return psycopg.connect(settings.SUPABASE_DB_DSN)


def insert_emotion_score_sql(payload: Dict[str, Any]) -> None:
    sql = (
        "insert into public.emotion_scores (session_id, role, label, confidence, timestamp) "
        "values (%(session_id)s, %(role)s, %(label)s, %(confidence)s, %(timestamp)s)"
    )
    with contextlib.closing(_get_conn()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, payload)
            conn.commit()


def insert_conversation_session_sql(data: Dict[str, Any]) -> None:
    cols = [
        "id",
        "transcript",
        "reply",
        "user_emotion_label",
        "user_emotion_confidence",
        "sophia_emotion_label",
        "sophia_emotion_confidence",
        "audio_url",
        "created_at",
    ]
    sql = (
        "insert into public.conversation_sessions (" + ",".join(cols) + ") values (" + ",".join([f"%({c})s" for c in cols]) + ")"
    )
    with contextlib.closing(_get_conn()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, data)
            conn.commit()
