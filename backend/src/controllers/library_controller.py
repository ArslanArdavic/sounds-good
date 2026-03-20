"""Controller for library sync endpoints (REST + WebSocket)."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from src.middleware.auth_middleware import get_current_user
from src.models.database import get_db
from src.models.user import User
from src.services.spotify_service import SpotifyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["library"])

# ---------------------------------------------------------------------------
# In-memory sync-state store.
# Key: str(user_id) → dict with keys: status, playlists_done, total_playlists,
#      tracks_done, error.
# In production this should be backed by Redis so multiple workers share state.
# ---------------------------------------------------------------------------
_sync_state: dict[str, dict[str, Any]] = {}


def _get_state(user_id: uuid.UUID) -> dict[str, Any]:
    return _sync_state.get(str(user_id), {"status": "idle"})


def _set_state(user_id: uuid.UUID, **kwargs: Any) -> None:
    _sync_state[str(user_id)] = {**_get_state(user_id), **kwargs}


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@router.post("/sync")
async def start_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Kick off an async library sync for the authenticated user.

    The sync runs as a background task; use ``GET /library/status`` or the
    WebSocket endpoint to track progress.

    Returns:
        ``{"status": "started"}``
    """
    user_id = current_user.id
    _set_state(user_id, status="syncing", playlists_done=0, total_playlists=0, tracks_done=0, error=None)

    async def run_sync() -> None:
        service = SpotifyService()
        try:
            async def on_progress(playlists_done: int, total_playlists: int, tracks_done: int) -> None:
                _set_state(
                    user_id,
                    status="syncing",
                    playlists_done=playlists_done,
                    total_playlists=total_playlists,
                    tracks_done=tracks_done,
                )

            result = await service.sync_library(user_id, db, on_progress=on_progress)
            _set_state(
                user_id,
                status="complete",
                playlists_done=result["playlists_synced"],
                total_playlists=result["playlists_synced"],
                tracks_done=result["tracks_synced"],
            )
            db.commit()
        except Exception as exc:
            logger.exception("Library sync failed for user %s: %s", user_id, exc)
            db.rollback()
            _set_state(user_id, status="error", error=str(exc))

    asyncio.create_task(run_sync())
    return {"status": "started"}


@router.get("/status")
def get_sync_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the current sync state for the authenticated user.

    Returns a dict with keys: ``status``, ``playlists_done``,
    ``total_playlists``, ``tracks_done``, ``error``.
    """
    return _get_state(current_user.id)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/sync/ws")
async def sync_progress_ws(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db),
) -> None:
    """Stream real-time sync progress over WebSocket.

    Connect with ``ws://<host>/library/sync/ws?token=<jwt>``.

    The server pushes JSON messages every 500 ms until the sync reaches
    ``complete`` or ``error``, then closes the connection.

    Message shape::

        {
            "status": "syncing" | "complete" | "error" | "idle",
            "playlists_done": int,
            "total_playlists": int,
            "tracks_done": int,
            "error": str | null
        }
    """
    from src.middleware.auth_middleware import get_current_user as _get_user
    from fastapi import HTTPException

    # Validate token manually (can't use Depends inside WebSocket handlers).
    try:
        user = _get_user(authorization=f"Bearer {token}", db=db)
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    try:
        while True:
            state = _get_state(user.id)
            await websocket.send_json(state)
            if state.get("status") in ("complete", "error"):
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for user %s", user.id)
    finally:
        await websocket.close()
