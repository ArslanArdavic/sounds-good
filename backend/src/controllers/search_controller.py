"""Controller for semantic track search (Phase 3 QA endpoint)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.middleware.auth_middleware import get_current_user
from src.models.database import get_db
from src.models.user import User
from src.schemas.request_schema import SearchTracksRequest
from src.schemas.track_schema import TrackResponse
from src.services.playlist_generation_service import PlaylistGenerationService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/tracks", response_model=list[TrackResponse])
def search_tracks(
    body: SearchTracksRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TrackResponse]:
    """Retrieve tracks from the user's library by semantic similarity.

    This endpoint exercises the full RAG retrieval pipeline: query embedding,
    vector search, and database hydration.  Useful for verifying search
    quality before the LLM playlist-generation step is wired up in Phase 4.
    """
    service = PlaylistGenerationService()
    tracks = service.retrieve_tracks(
        db,
        current_user.id,
        body.query,
        n_results=body.n_results,
        max_distance=body.max_distance,
    )
    return [TrackResponse.model_validate(t) for t in tracks]
