"""FastAPI entry point that wires endpoints, middleware, telemetry, and voice pipelines."""

import os
import time
import logging
from typing import Sequence

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import get_settings
from app.config_validation import validate_settings
from app.deps import verify_api_key, limiter
from app.services import supabase as supabase_service
from app.tracing import setup_tracer
from app.routers import chat as chat_router, admin as admin_router, evaluation as evaluation_router
from dotenv import load_dotenv

load_dotenv()

_START_TIME = time.perf_counter()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sophia-backend")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces API-key authentication on every non-public HTTP route."""

    def __init__(self, app: FastAPI, public_paths: Sequence[str]):
        super().__init__(app)
        self.public_paths = public_paths or []

    def _is_public(self, path: str) -> bool:
        """Return True when request path matches a configured public route."""
        for pattern in self.public_paths:
            if pattern == "*":
                return True
            if pattern.endswith("/*"):
                prefix = pattern[:-2]
                if path.startswith(prefix):
                    return True
            if path == pattern:
                return True
            # Allow prefix-style matches without needing explicit wildcard
            if (
                pattern
                and pattern != "/"
                and path.startswith(pattern.rstrip("/") + "/")
            ):
                return True
        return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.method == "OPTIONS":
            return await call_next(request)
        if self._is_public(request.url.path):
            return await call_next(request)
        authorization = request.headers.get("Authorization")
        try:
            verify_api_key(request=request, authorization=authorization)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code, content={"detail": exc.detail}
            )
        return await call_next(request)


settings = get_settings()
validate_settings(settings)

app = FastAPI(title=settings.APP_NAME)

setup_tracer(app, settings)
supabase_service.init_supabase(settings)

app.add_middleware(APIKeyMiddleware, public_paths=settings.API_PUBLIC_PATHS)

allowed_cors_origins = settings.CORS_ALLOWED_ORIGINS or ["http://localhost:3000"]
logger.info("Configuring CORS for allowed origins: %s", allowed_cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-Api-Key",
    ],
    expose_headers=["Authorization"],
    max_age=86400,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files for frontend (only if frontend directory exists)
# In backend-only deployment (Render), frontend is served separately by Vercel
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
    logger.info("Frontend static files mounted at /frontend")
else:
    logger.info(
        "Frontend directory not found - running in backend-only mode (frontend served by Vercel)"
    )

app.include_router(admin_router.router)
app.include_router(chat_router.router)
app.include_router(evaluation_router.router)

@app.get("/health")
def health():
    """Basic liveness endpoint."""
    return {"status": "ok"}


@app.get("/")
def root(request: Request):
    """Backend status with optional static frontend response."""
    accepts = request.headers.get("accept", "")
    if "text/html" in accepts.lower() and os.path.exists("frontend/index.html"):
        # Full-stack deployment: serve frontend to browser clients requesting HTML
        return FileResponse("frontend/index.html")

    # Backend-only deployment: return API info (default for API clients/tests)
    return {
        "message": "Sophia AI Backend is running",
        "frontend_url": "https://sophia-1st-mvp-git-main-davidelavergas-projects.vercel.app",
        "api_status": "ok",
        "deployment_mode": "backend+api"
        if os.path.exists("frontend/index.html")
        else "backend-only",
        "docs_url": "/docs",
    }

logger.info(
    "Startup initialization completed in %.2f s", time.perf_counter() - _START_TIME
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
