from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import events as events_router

# Load env vars from .env for local/dev usage. In deployment, env vars may be injected.
load_dotenv()

openapi_tags: list[dict[str, Any]] = [
    {"name": "health", "description": "Service health and diagnostics endpoints."},
    {"name": "events", "description": "Event CRUD plus RSVPs and comments."},
]

app = FastAPI(
    title="Local Events Backend",
    description=(
        "Simple local events platform backend.\n\n"
        "Auth is intentionally lightweight for MVP: the frontend sends a user identity via `X-User-Id` header "
        "(a UUID). The backend uses it for ownership checks (create/update/delete) and attribution "
        "(created_by on events/comments, and RSVPs).\n\n"
        "If `X-User-Id` is missing, endpoints that require identity will return 401."
    ),
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# CORS configuration
allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:3000"]

allowed_headers = [h.strip() for h in os.getenv("ALLOWED_HEADERS", "").split(",") if h.strip()]
if not allowed_headers:
    allowed_headers = ["Content-Type", "Authorization", "X-Requested-With", "X-User-Id"]

allowed_methods = [m.strip() for m in os.getenv("ALLOWED_METHODS", "").split(",") if m.strip()]
if not allowed_methods:
    allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

cors_max_age = int(os.getenv("CORS_MAX_AGE", "3600"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
    max_age=cors_max_age,
)


@app.get(
    os.getenv("HEALTHCHECK_PATH", "/healthz"),
    tags=["health"],
    summary="Health check",
    description="Simple health check endpoint used by orchestration/CI.",
    operation_id="healthz",
)
def healthz() -> dict[str, str]:
    """Return a minimal health status payload."""
    return {"status": "ok"}


app.include_router(events_router.router)
