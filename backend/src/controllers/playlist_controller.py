"""Playlist generation (Phase 4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.middleware.auth_middleware import get_current_user
from src.models.database import get_db
from src.models.user import User
from src.schemas.playlist_schema import PlaylistResponse
from src.schemas.request_schema import GeneratePlaylistRequest
from src.services.playlist_generation_service import PlaylistGenerationService

router = APIRouter(prefix="/playlist", tags=["playlist"])


@router.post("/generate", response_model=PlaylistResponse)
def generate_playlist(
    body: GeneratePlaylistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaylistResponse:
    """Generate a playlist from natural language using RAG + Groq LLM."""
    service = PlaylistGenerationService()
    playlist = service.generate_playlist(db, current_user.id, body.text)
    db.commit()
    return PlaylistResponse.model_validate(playlist)
