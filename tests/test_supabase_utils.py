import uuid
from types import SimpleNamespace

import app.services.supabase as supabase


class StubTable:
    def __init__(self, bucket):
        self.bucket = bucket
        self.payloads = []

    def insert(self, payload):
        self.payloads.append(payload)
        return self

    def execute(self):
        return SimpleNamespace(data=self.payloads[-1])


class StubSupabase:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        table = self.tables.setdefault(name, StubTable(name))
        return table

    def storage(self):  # pragma: no cover - not used in these tests
        raise NotImplementedError


def setup_module():
    supabase._supabase = StubSupabase()
    supabase._DEFAULT_USER_ID = None


def teardown_module():
    supabase._supabase = None
    supabase._DEFAULT_USER_ID = None


def test_user_uuid_from_discord_deterministic():
    uid1 = supabase.user_uuid_from_discord("discord-user-42")
    uid2 = supabase.user_uuid_from_discord("discord-user-42")
    assert uid1 == uid2
    assert uuid.UUID(uid1).version == 5


def test_insert_conversation_session_derives_user_id_from_discord():
    supabase._supabase = StubSupabase()
    session_id = "test-session"
    supabase.insert_conversation_session({
        "id": session_id,
        "transcript": "Hi",
        "reply": "Hello",
        "discord_id": "discord-abc",
    })
    table = supabase._supabase.tables["conversation_sessions"]
    assert table.payloads[-1]["id"] == session_id
    assert table.payloads[-1]["user_id"] == supabase.user_uuid_from_discord("discord-abc")


def test_insert_emotion_score_applies_resolved_user_id():
    supabase._supabase = StubSupabase()
    supabase.insert_emotion_score(
        session_id="sess-1",
        role="user",
        emotion=SimpleNamespace(label="neutral", confidence=0.5),
        discord_id="discord-xyz",
    )
    table = supabase._supabase.tables["emotion_scores"]
    payload = table.payloads[-1]
    assert payload["role"] == "user"
    assert payload["user_id"] == supabase.user_uuid_from_discord("discord-xyz")


def test_user_uuid_from_discord_handles_none():
    assert supabase.user_uuid_from_discord(None) is None
