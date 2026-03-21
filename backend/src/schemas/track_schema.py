import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class TrackResponse(BaseModel):
    id: uuid.UUID
    spotify_track_id: str
    name: str
    artist: str
    duration_ms: int
    audio_features: dict[str, Any] | None = None
    cached_at: datetime

    @field_validator("audio_features", mode="before")
    @classmethod
    def deserialize_audio_features(cls, v: object) -> dict[str, Any] | None:
        if isinstance(v, str):
            return json.loads(v)
        return v  # type: ignore[return-value]

    model_config = {"from_attributes": True}
