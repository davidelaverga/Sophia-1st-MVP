from fastapi import Header, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import get_settings
from app.services.supabase import has_user_consent

limiter = Limiter(key_func=get_remote_address)


def verify_api_key(authorization: str | None = Header(default=None)) -> None:
    """
    Enforces header-based API key in the form: Authorization: Bearer <KEY>
    If API_KEYS env var lists keys, require membership; otherwise accept any non-empty token.
    """
    settings = get_settings()

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    provided = authorization.split(" ", 1)[1].strip()
    if not provided:
        raise HTTPException(status_code=401, detail="Empty API key")

    if settings.API_KEYS:
        if provided not in settings.API_KEYS:
            raise HTTPException(status_code=401, detail="Unauthorized")
    # If no API_KEYS configured, allow any non-empty token (useful for local dev)
    return None


def require_consent(x_discord_id: str | None = Header(default=None)) -> None:
    """Require GDPR consent before allowing voice/chat endpoints.

    Frontend must set `X-Discord-Id` header after Discord OAuth. We then check
    Supabase table `user_consents` for a record. If none, reject with 403.
    """
    settings = get_settings()
    # Allow bypass in local dev if explicitly disabled
    if getattr(settings, "REQUIRE_CONSENT", "true").lower() in {"0", "false", "no"}:
        return None

    if not x_discord_id:
        raise HTTPException(status_code=403, detail="Consent required: missing X-Discord-Id header")

    if not has_user_consent(x_discord_id):
        raise HTTPException(status_code=403, detail="Consent required. Please accept data processing consent.")

    return None
