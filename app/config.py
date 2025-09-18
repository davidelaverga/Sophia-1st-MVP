import os
from functools import lru_cache
from dotenv import load_dotenv, find_dotenv

# Load .env as early as possible so Settings reads populated values.
# find_dotenv() will search parent directories to locate the .env file.
load_dotenv(find_dotenv(), override=False)


class Settings:
    APP_NAME: str = "Sophia Voice Backend"
    API_RATE_LIMIT: str = os.getenv("API_RATE_LIMIT", "30/minute")

    # Auth
    API_KEYS: list[str] = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]

    # External services
    MISTRAL_API_KEY: str | None = os.getenv("MISTRAL_API_KEY")
    INWORLD_API_KEY: str | None = os.getenv("INWORLD_API_KEY")  # Base64 Basic token
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    
    # Redis for memory caching
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # Supabase (HTTP client for storage/REST)
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str | None = os.getenv("SUPABASE_KEY")
    SUPABASE_BUCKET_AUDIO: str = os.getenv("SUPABASE_BUCKET_AUDIO", "Audio Storage")
    SUPABASE_AUDIO_PREFIX: str = os.getenv("SUPABASE_AUDIO_PREFIX", "uploads/")

    # Optional: direct Postgres via Transaction Pooler
    SUPABASE_DB_DSN: str | None = os.getenv("SUPABASE_DB_DSN")

    # OpenTelemetry (OTLP HTTP exporter)
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    OTEL_EXPORTER_OTLP_HEADERS: str | None = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
