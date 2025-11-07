"""FastAPI dependencies for API-key auth, rate limiting, and consent enforcement."""

from typing import Optional
import threading
from urllib.parse import urljoin
from fastapi import Header, HTTPException, Request
from jwt import InvalidTokenError, PyJWKClient, decode as jwt_decode, get_unverified_header
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import get_settings
from app.services.supabase import has_user_consent

limiter = Limiter(key_func=get_remote_address)

_JWK_CLIENTS: dict[str, PyJWKClient] = {}
_JWK_CLIENT_LOCK = threading.Lock()


def _build_jwks_url(issuer: str) -> str:
    base = issuer if issuer.endswith("/") else f"{issuer}/"
    return urljoin(base, ".well-known/jwks.json")


def _get_jwk_client(issuer: str) -> PyJWKClient:
    jwks_url = _build_jwks_url(issuer)
    with _JWK_CLIENT_LOCK:
        client = _JWK_CLIENTS.get(jwks_url)
        if client is None:
            client = PyJWKClient(jwks_url)
            _JWK_CLIENTS[jwks_url] = client
    return client


def _verify_jwt_signature_via_jwks(token: str) -> None:
    try:
        unverified_claims = jwt_decode(token, options={"verify_signature": False})
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Unauthorized: malformed token") from exc

    issuer = unverified_claims.get("iss")
    if not issuer or not isinstance(issuer, str):
        raise HTTPException(status_code=401, detail="Unauthorized: issuer claim missing")

    jwk_client = _get_jwk_client(issuer)
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
    except Exception as exc:  # noqa: BLE001 - propagate as auth failure
        raise HTTPException(status_code=401, detail="Unauthorized: unable to resolve signing key") from exc

    header = get_unverified_header(token)
    header_alg = header.get("alg") if isinstance(header, dict) else None
    algorithm = signing_key.algorithm_name or header_alg
    if not algorithm:
        raise HTTPException(status_code=401, detail="Unauthorized: unknown signing algorithm")

    try:
        jwt_decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            options={
                "verify_signature": True,
                "verify_exp": False,
                "verify_aud": False,
                "verify_iat": False,
                "verify_nbf": False,
                "verify_iss": False,
                "verify_sub": False,
            },
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid token signature") from exc


def extract_user_id_from_token(token: Optional[str]) -> Optional[str]:
    """Return the Supabase user id embedded in the JWT (the `sub` claim)."""
    if not token:
        return None
    try:
        claims = jwt_decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
                "verify_iat": False,
                "verify_nbf": False,
            },
        )
    except InvalidTokenError:
        return None

    sub = claims.get("sub")
    if isinstance(sub, str) and sub:
        return sub

    user = claims.get("user")
    if isinstance(user, dict):
        user_id = user.get("id")
        if isinstance(user_id, str) and user_id:
            return user_id

    return None


def verify_api_key(
    request: Request = None,
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Validate that the request carries a Supabase JWT with a valid signature."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    _verify_jwt_signature_via_jwks(token)
    if request is not None:
        request.state.supabase_token = token
        request.state.supabase_user_id = extract_user_id_from_token(token)
    return token


def require_consent(
    request: Request = None,
    x_discord_id: Optional[str] = Header(default=None),
    supabase_token: Optional[str] = None,
) -> None:
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

    token = supabase_token
    if token is None and request is not None:
        token = getattr(request.state, "supabase_token", None)

    if not has_user_consent(x_discord_id, access_token=token):
        raise HTTPException(status_code=403, detail="Consent required. Please accept data processing consent.")

    return None
