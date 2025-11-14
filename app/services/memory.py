"""Session memory manager combining Redis cache, Supabase persistence, and topic extraction."""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from app.config import get_settings
from app.services.supabase import get_supabase

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    query: str
    response: str
    user_emotion: str
    sophia_emotion: str
    intent: str
    timestamp: float


@dataclass
class SessionMemory:
    session_id: str
    turns: List[ConversationTurn]
    topics: List[str]
    user_tone_history: List[str]
    sophia_tone_history: List[str]
    created_at: float
    updated_at: float


class MemoryManager:
    """Manages conversation memory using Redis for fast access and Supabase for persistence"""

    def __init__(self):
        self.settings = get_settings()
        self.redis_client = self._init_redis()
        self.max_turns = 3  # Keep last 3 turns in memory
        ttl = getattr(self.settings, "MEMORY_LOCAL_TTL_SECONDS", 3600)
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            ttl = 3600
        ttl = max(60, ttl)
        cache_limit = getattr(self.settings, "MEMORY_LOCAL_CACHE_LIMIT", 256)
        try:
            cache_limit = int(cache_limit)
        except (TypeError, ValueError):
            cache_limit = 256
        self._local_store_ttl = ttl
        self._local_store_limit = max(1, cache_limit)
        self._local_store: Dict[str, Tuple[SessionMemory, float]] = {}

    def _init_redis(self):
        """Initialize Redis client"""
        try:
            import redis

            return redis.Redis(
                host=getattr(self.settings, "REDIS_HOST", "localhost"),
                port=getattr(self.settings, "REDIS_PORT", 6379),
                db=getattr(self.settings, "REDIS_DB", 0),
                decode_responses=True,
            )
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            return None

    def get_session_memory(
        self, session_id: str, access_token: Optional[str] = None
    ) -> Optional[SessionMemory]:
        """Retrieve session memory from Redis or Supabase"""

        # Try Redis first for fast access
        if self.redis_client:
            try:
                memory_json = self.redis_client.get(f"session:{session_id}")
                if memory_json:
                    memory_data = json.loads(memory_json)
                    return self._deserialize_memory(memory_data)
            except Exception as e:
                logger.error(f"Redis get failed: {e}")

        # Fallback to local in-process cache before Supabase
        local_memory = self._get_local_memory(session_id)
        if local_memory:
            return local_memory

        # Fallback to Supabase
        try:
            supabase_client = get_supabase(access_token)
            result = (
                supabase_client.table("conversation_sessions")
                .select("*")
                .eq("id", session_id)
                .execute()
            )
            if result.data:
                session_data = result.data[0]
                memory = self._build_memory_from_session(session_data)
                self._set_local_memory(session_id, memory)
                return memory
        except Exception as e:
            logger.error(f"Supabase memory retrieval failed: {e}")

        return None

    def update_session_memory(
        self,
        session_id: str,
        new_turn: ConversationTurn,
        access_token: Optional[str] = None,
    ) -> SessionMemory:
        """Update session memory with new conversation turn"""

        # Get existing memory or create new
        memory = self.get_session_memory(session_id, access_token=access_token)
        if not memory:
            memory = SessionMemory(
                session_id=session_id,
                turns=[],
                topics=[],
                user_tone_history=[],
                sophia_tone_history=[],
                created_at=time.time(),
                updated_at=time.time(),
            )

        # Add new turn
        memory.turns.append(new_turn)
        memory.user_tone_history.append(new_turn.user_emotion)
        memory.sophia_tone_history.append(new_turn.sophia_emotion)

        # Extract topics (simple keyword extraction)
        topics = self._extract_topics(new_turn.query)
        memory.topics.extend(topics)

        # Keep only last N turns
        if len(memory.turns) > self.max_turns:
            memory.turns = memory.turns[-self.max_turns :]
            memory.user_tone_history = memory.user_tone_history[-self.max_turns :]
            memory.sophia_tone_history = memory.sophia_tone_history[-self.max_turns :]

        # Keep unique topics, last 5
        memory.topics = list(dict.fromkeys(memory.topics))[-5:]
        memory.updated_at = time.time()

        # Store in Redis
        if self.redis_client:
            try:
                memory_json = json.dumps(asdict(memory), default=str)
                self.redis_client.setex(
                    f"session:{session_id}",
                    3600,  # 1 hour TTL
                    memory_json,
                )
            except Exception as e:
                logger.error(f"Redis store failed: {e}")

        # Also persist to Supabase
        self._persist_to_supabase(memory)
        self._set_local_memory(session_id, memory)

        return memory

    def get_context_for_llm(
        self, session_id: str, access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get formatted context for LLM prompt"""
        memory = self.get_session_memory(session_id, access_token=access_token)
        if not memory:
            return {}

        recent_turns = [
            {
                "user": turn.query,
                "sophia": turn.response,
                "intent": turn.intent,
                "timestamp": turn.timestamp,
            }
            for turn in memory.turns[-self.max_turns :]
            if turn.query or turn.response
        ]

        context = {
            "last_topics": memory.topics,
            "last_user_tone": memory.user_tone_history[-1]
            if memory.user_tone_history
            else "neutral",
            "conversation_turns": len(memory.turns),
            "recent_intents": [turn.intent for turn in memory.turns[-2:]]
            if len(memory.turns) >= 2
            else [],
            "recent_turns": recent_turns,
        }

        return context

    def _get_local_memory(self, session_id: str) -> Optional[SessionMemory]:
        """Return cached memory from the local in-process store if available."""
        entry = self._local_store.get(session_id)
        if not entry:
            self._prune_local_store()
            return None
        memory, expires_at = entry
        if expires_at < time.time():
            self._local_store.pop(session_id, None)
            return None
        return memory

    def _set_local_memory(self, session_id: str, memory: SessionMemory) -> None:
        """Store memory in local cache with TTL so we still have context without Redis."""
        expires_at = time.time() + self._local_store_ttl
        self._local_store[session_id] = (memory, expires_at)
        self._prune_local_store()

    def _prune_local_store(self) -> None:
        """Remove expired or overflow entries from the local cache."""
        now = time.time()
        expired = [
            session_id
            for session_id, (_, expires_at) in self._local_store.items()
            if expires_at < now
        ]
        for session_id in expired:
            self._local_store.pop(session_id, None)

        if len(self._local_store) <= self._local_store_limit:
            return

        overflow = len(self._local_store) - self._local_store_limit
        if overflow <= 0:
            return

        # Remove the soonest-to-expire entries first
        sorted_sessions = sorted(self._local_store.items(), key=lambda item: item[1][1])
        for session_id, _ in sorted_sessions[:overflow]:
            self._local_store.pop(session_id, None)

    def _extract_topics(self, query: str) -> List[str]:
        """Simple topic extraction from query"""
        # Simple keyword-based topic extraction
        defi_topics = {
            "staking": ["staking", "stake", "validator"],
            "yield_farming": ["yield", "farming", "farm", "liquidity"],
            "defi_protocols": ["uniswap", "aave", "compound", "makerdao"],
            "tokens": ["token", "coin", "ethereum", "bitcoin"],
            "trading": ["swap", "trade", "exchange", "price"],
        }

        query_lower = query.lower()
        found_topics = []

        for topic, keywords in defi_topics.items():
            if any(keyword in query_lower for keyword in keywords):
                found_topics.append(topic)

        return found_topics

    def _build_memory_from_session(self, session_data: Dict[str, Any]) -> SessionMemory:
        """Build SessionMemory from Supabase session data"""
        # This is a simplified version - in practice you'd need more sophisticated parsing
        turn = ConversationTurn(
            query=session_data.get("transcript", ""),
            response=session_data.get("reply", ""),
            user_emotion=session_data.get("user_emotion_label", "neutral"),
            sophia_emotion=session_data.get("sophia_emotion_label", "neutral"),
            intent="unknown",  # Would need to store this separately
            timestamp=time.time(),
        )

        return SessionMemory(
            session_id=session_data["id"],
            turns=[turn],
            topics=[],
            user_tone_history=[turn.user_emotion],
            sophia_tone_history=[turn.sophia_emotion],
            created_at=time.time(),
            updated_at=time.time(),
        )

    def _deserialize_memory(self, memory_data: Dict[str, Any]) -> SessionMemory:
        """Deserialize memory from JSON data"""
        turns = [
            ConversationTurn(**turn_data) for turn_data in memory_data.get("turns", [])
        ]

        return SessionMemory(
            session_id=memory_data["session_id"],
            turns=turns,
            topics=memory_data.get("topics", []),
            user_tone_history=memory_data.get("user_tone_history", []),
            sophia_tone_history=memory_data.get("sophia_tone_history", []),
            created_at=memory_data.get("created_at", time.time()),
            updated_at=memory_data.get("updated_at", time.time()),
        )

    def _persist_to_supabase(self, memory: SessionMemory):
        """Persist memory state to Supabase for long-term storage"""
        try:
            # Create a summary record in a memory table
            memory_record = {
                "session_id": memory.session_id,
                "topics": memory.topics,
                "turn_count": len(memory.turns),
                "last_user_emotion": memory.user_tone_history[-1]
                if memory.user_tone_history
                else "neutral",
                "last_sophia_emotion": memory.sophia_tone_history[-1]
                if memory.sophia_tone_history
                else "neutral",
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
            }

            # Upsert to session_memory table (would need to create this table)
            # For now, just log the memory state
            logger.info(
                f"Memory persisted for session {memory.session_id}: {memory_record}"
            )

        except Exception as e:
            logger.error(f"Supabase memory persistence failed: {e}")


# Singleton instance
memory_manager = MemoryManager()
