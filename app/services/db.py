import contextlib
import logging
from typing import Any, Dict
import psycopg

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_conn():
    """Get database connection"""
    settings = get_settings()
    if not settings.SUPABASE_DB_DSN:
        raise RuntimeError("SUPABASE_DB_DSN not configured")
    return psycopg.connect(settings.SUPABASE_DB_DSN)


def insert_emotion_score_sql(payload: Dict[str, Any]) -> None:
    """Insert emotion score using direct SQL
    
    Table schema:
    - id (uuid, auto-generated)
    - session_id (uuid) - foreign key to conversation_sessions
    - role (text) - 'user' or 'sophia'
    - label (text)
    - confidence (double precision) - 0.0 to 1.0
    - timestamp (timestamptz, auto)
    - created_at (timestamptz, auto)
    
    Note: No user_id column in this table
    """
    sql = (
        "INSERT INTO public.emotion_scores "
        "(session_id, role, label, confidence) "
        "VALUES (%(session_id)s::uuid, %(role)s, %(label)s, %(confidence)s)"
    )
    try:
        with contextlib.closing(_get_conn()) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, payload)
                conn.commit()
        logger.debug(f"✅ Emotion score inserted via SQL: {payload['session_id']}")
    except Exception as e:
        logger.error(f"❌ SQL insert_emotion_score failed: {e}")
        raise


def insert_conversation_session_sql(data: Dict[str, Any]) -> None:
    """Insert conversation session using direct SQL
    
    Matches actual database schema:
    - id (uuid)
    - user_id (text)
    - transcript (text)
    - response (text)
    - audio_url (text)
    - response_audio_url (text)
    - user_emotion (jsonb)
    - sophia_emotion (jsonb)
    - source (text)
    - latency (double precision)
    - timestamp (timestamptz) - auto
    - created_at (timestamptz) - auto
    """
    
    # Build column list based on what's in data
    cols = []
    if "id" in data:
        cols.append("id")
    if "user_id" in data:
        cols.append("user_id")
    if "transcript" in data:
        cols.append("transcript")
    if "response" in data:
        cols.append("response")
    if "audio_url" in data:
        cols.append("audio_url")
    if "response_audio_url" in data:
        cols.append("response_audio_url")
    if "user_emotion" in data:
        cols.append("user_emotion")
    if "sophia_emotion" in data:
        cols.append("sophia_emotion")
    if "source" in data:
        cols.append("source")
    if "latency" in data:
        cols.append("latency")
    
    if not cols:
        logger.error("No valid columns to insert")
        return
    
    # Build SQL dynamically
    placeholders = ",".join([f"%({c})s" for c in cols])
    col_names = ",".join(cols)
    
    sql = f"INSERT INTO public.conversation_sessions ({col_names}) VALUES ({placeholders})"
    
    try:
        with contextlib.closing(_get_conn()) as conn:
            with conn.cursor() as cur:
                # Filter data to only include columns we're inserting
                filtered_data = {k: v for k, v in data.items() if k in cols}
                
                # Convert JSONB fields to proper format
                if "user_emotion" in filtered_data:
                    import json
                    filtered_data["user_emotion"] = json.dumps(filtered_data["user_emotion"])
                if "sophia_emotion" in filtered_data:
                    import json
                    filtered_data["sophia_emotion"] = json.dumps(filtered_data["sophia_emotion"])
                
                cur.execute(sql, filtered_data)
                conn.commit()
        logger.info(f"✅ Conversation session inserted via SQL: {data.get('id', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ SQL insert_conversation_session failed: {e}")
        logger.error(f"   SQL: {sql}")
        logger.error(f"   Data: {data}")
        raise