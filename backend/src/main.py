from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.controllers.auth_controller import router as auth_router
from src.middleware.error_handler import register_error_handlers
from src.models import database  # noqa: F401 — ensures engine is initialised
from src.models import playlist, spotify_token, track, user  # noqa: F401 — registers models with Base.metadata

settings = get_settings()

app = FastAPI(
    title="Sounds Good",
    description="AI-powered playlist generation from your Spotify library.",
    version="0.1.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(auth_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
