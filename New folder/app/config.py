import os
from functools import lru_cache


class Settings:
    APP_NAME: str = "Sophia Voice Backend"
    API_RATE_LIMIT: str = os.getenv("API_RATE_LIMIT", "30/minute")

    # Auth
    API_KEYS: list[str] = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]

    # External services
    MISTRAL_API_KEY: str | None = os.getenv("MISTRAL_API_KEY")
    INWORLD_API_KEY: str | None = os.getenv("INWORLD_API_KEY")  # Base64 Basic token

    # Supabase (HTTP client for storage/REST)
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str | None = os.getenv("SUPABASE_KEY")
    SUPABASE_BUCKET_AUDIO: str = os.getenv("SUPABASE_BUCKET_AUDIO", "audio")
    SUPABASE_AUDIO_PREFIX: str = os.getenv("SUPABASE_AUDIO_PREFIX", "uploads/")

    # Optional: direct Postgres via Transaction Pooler
    SUPABASE_DB_DSN: str | None = os.getenv("SUPABASE_DB_DSN")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
