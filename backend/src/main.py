from datetime import datetime, timezone

from dotenv import load_dotenv

# Load .env into os.environ so optional vars (e.g. HF_TOKEN) are visible to
# Hugging Face / sentence-transformers, not only to Pydantic Settings fields.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.controllers.auth_controller import router as auth_router
from src.controllers.library_controller import router as library_router
from src.controllers.playlist_controller import router as playlist_router
from src.controllers.search_controller import router as search_router
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
app.include_router(library_router)
app.include_router(search_router)
app.include_router(playlist_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
