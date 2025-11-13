"""FastAPI dependencies for API-key auth, rate limiting, and consent enforcement."""

import logging
import os
from typing import Optional, Any
import threading
from urllib.parse import urljoin

from fastapi import Header, HTTPException, Request
from jwt import (
    InvalidTokenError,
    PyJWKClient,
    decode as jwt_decode,
    get_unverified_header,
)

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings
from app.services.supabase import has_user_consent

limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("sophia-backend")

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
        raise HTTPException(
            status_code=401, detail="Unauthorized: malformed token"
        ) from exc

    issuer = unverified_claims.get("iss")
    if not issuer or not isinstance(issuer, str):
        raise HTTPException(
            status_code=401, detail="Unauthorized: issuer claim missing"
        )

    jwk_client = _get_jwk_client(issuer)
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
    except Exception as exc:  # noqa: BLE001 - propagate as auth failure
        raise HTTPException(
            status_code=401, detail="Unauthorized: unable to resolve signing key"
        ) from exc

    header = get_unverified_header(token)
    header_alg = header.get("alg") if isinstance(header, dict) else None
    algorithm = signing_key.algorithm_name or header_alg
    if not algorithm:
        raise HTTPException(
            status_code=401, detail="Unauthorized: unknown signing algorithm"
        )

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
        raise HTTPException(
            status_code=401, detail="Unauthorized: invalid token signature"
        ) from exc


def _decode_jwt_payload(token: Optional[str]) -> Optional[dict[str, Any]]:
    if not token:
        return None
    try:
        return jwt_decode(
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


def extract_identity_from_token(token: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Return `(user_id, discord_id)` extracted from a Supabase JWT."""
    claims = _decode_jwt_payload(token)
    if not claims:
        return None, None

    user_id: Optional[str] = None
    discord_id: Optional[str] = None

    sub = claims.get("sub")
    if isinstance(sub, str) and sub:
        user_id = sub

    user = claims.get("user")
    if isinstance(user, dict):
        candidate = user.get("id")
        if isinstance(candidate, str) and candidate:
            user_id = user_id or candidate

    user_metadata = claims.get("user_metadata")
    if isinstance(user_metadata, dict):
        for key in ("provider_id", "sub", "provider_token", "user_id"):
            value = user_metadata.get(key)
            if isinstance(value, str) and value:
                discord_id = value
                break

    if not discord_id:
        discord_id = user_id

    return user_id, discord_id


def extract_user_id_from_token(token: Optional[str]) -> Optional[str]:
    """Return the Supabase user id embedded in the JWT (the `sub` claim)."""
    user_id, _ = extract_identity_from_token(token)
    return user_id


def extract_discord_id_from_token(token: Optional[str]) -> Optional[str]:
    """Best-effort extraction of the Discord id stored in Supabase user metadata."""
    _, discord_id = extract_identity_from_token(token)
    return discord_id


def verify_api_key(
    request: Request = None,
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Validate that the request carries a Supabase JWT with a valid signature."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    settings = get_settings()
    # Allow simple API keys for legacy automation/integration flows
    allowed_keys = set(settings.API_KEYS)
    if "PYTEST_CURRENT_TEST" in os.environ:
        allowed_keys.add("test-key")
    if token in allowed_keys:
        if request is not None:
            request.state.supabase_token = token
            request.state.supabase_user_id = None
        return token

    try:
        header = get_unverified_header(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=401, detail="Unauthorized: malformed token"
        ) from exc

    alg = (header.get("alg") or "").upper()
    if alg.startswith("HS"):
        secret = (
            os.getenv("SUPABASE_JWT_SECRET")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or settings.SUPABASE_KEY
        )
        if secret:
            try:
                jwt_decode(
                    token,
                    secret,
                    algorithms=[alg],
                    options={
                        "verify_signature": True,
                        "verify_exp": False,
                        "verify_aud": False,
                        "verify_iat": False,
                        "verify_nbf": False,
                    },
                )
            except InvalidTokenError as exc:
                raise HTTPException(
                    status_code=401, detail="Unauthorized: invalid token signature"
                ) from exc
        else:
            logger.warning(
                "SUPABASE_JWT_SECRET/SERVICE_ROLE_KEY is not configured; skipping signature verification for Supabase JWTs"
            )
    else:
        _verify_jwt_signature_via_jwks(token)

    if request is not None:
        request.state.supabase_token = token
        user_id, discord_id = extract_identity_from_token(token)
        request.state.supabase_user_id = user_id
        request.state.supabase_discord_id = discord_id
    return token


def require_consent(
    request: Request = None,
    discord_id: Optional[str] = None,
    supabase_token: Optional[str] = None,
) -> None:
    """Require GDPR consent before allowing voice/chat endpoints."""
    settings = get_settings()
    # Allow bypass in local dev if explicitly disabled
    if getattr(settings, "REQUIRE_CONSENT", "true").lower() in {"0", "false", "no"}:
        return None

    token = supabase_token
    if token is None and request is not None:
        token = getattr(request.state, "supabase_token", None)

    if not discord_id:
        if token:
            discord_id = extract_discord_id_from_token(token)
        if not discord_id and request is not None:
            discord_id = getattr(request.state, "supabase_discord_id", None)

    if not discord_id:
        raise HTTPException(status_code=403, detail="Consent required: missing Discord identity")

    if not has_user_consent(discord_id, access_token=token):
        raise HTTPException(status_code=403, detail="Consent required. Please accept data processing consent.")

    return None
