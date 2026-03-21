"""Playlist generation (Phase 4) and Spotify save (Phase 5)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.middleware.auth_middleware import get_current_user
from src.middleware.error_handler import ConflictError, NotFoundError
from src.models.database import get_db
from src.models.user import User
from src.repositories.playlist_repository import PlaylistRepository
from src.schemas.playlist_schema import PlaylistResponse
from src.schemas.request_schema import GeneratePlaylistRequest
from src.services.playlist_generation_service import PlaylistGenerationService
from src.services.spotify_service import SpotifyService

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


@router.post("/{playlist_id}/save-to-spotify", response_model=PlaylistResponse)
async def save_playlist_to_spotify(
    playlist_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaylistResponse:
    """Create this playlist on Spotify and link ``spotify_playlist_id`` locally."""
    repo = PlaylistRepository()
    playlist = repo.get_with_tracks(db, playlist_id)
    if playlist is None or playlist.user_id != current_user.id:
        raise NotFoundError("Playlist not found")
    if playlist.spotify_playlist_id is not None:
        raise ConflictError("Playlist already saved to Spotify")

    service = SpotifyService()
    updated = await service.save_playlist_to_spotify(db, current_user, playlist)
    db.commit()
    return PlaylistResponse.model_validate(updated)
