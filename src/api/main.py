from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
load_dotenv()  # loads .env for local dev; no-op when env vars already set (Railway)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.api.middleware import limiter, _rate_limit_exceeded_handler
from src.api.schemas import HealthResponse
from src.api.state import SESSION_STORE, SESSION_TTL_HOURS, SessionNotFoundError, LLMError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Blom Matching API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nitinmohan.dev",
        "https://operator.blom.social",
        "https://blom-matching.vercel.app",
        "http://localhost:5173",
    ],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "X-Session-Token", "Content-Type"],
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(ValidationError)
async def validation_error_handler(_request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": str(exc)})


@app.exception_handler(SessionNotFoundError)
async def session_not_found_handler(_request, _exc: SessionNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": "session_not_found",
            "detail": "Session expired or not found. Please reload the event.",
        },
    )


@app.exception_handler(LLMError)
async def llm_error_handler(_request, exc: LLMError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "llm_unavailable",
            "detail": str(exc),
            "result": exc.raw_result,
        },
    )


# ---------------------------------------------------------------------------
# Session cleanup background task
# ---------------------------------------------------------------------------

async def _cleanup_sessions() -> None:
    while True:
        await asyncio.sleep(60)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=SESSION_TTL_HOURS)
        expired = [
            token
            for token, session in SESSION_STORE.items()
            if datetime.fromisoformat(session["created_at"]) < cutoff
        ]
        for token in expired:
            del SESSION_STORE[token]
        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(_cleanup_sessions())
    logger.info("Blom Matching API started")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from src.api.routes.events import router as events_router          # noqa: E402
from src.api.routes.matching import router as matching_router      # noqa: E402
from src.api.routes.users import router as users_router            # noqa: E402
from src.api.routes.evaluation import router as evaluation_router  # noqa: E402
from src.api.routes.demo import router as demo_router              # noqa: E402

app.include_router(events_router, prefix="/api")
app.include_router(matching_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api")
app.include_router(demo_router, prefix="/api")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0", llm_available=True)
