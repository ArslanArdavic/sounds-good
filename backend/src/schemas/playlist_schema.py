import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field

from src.schemas.track_schema import TrackResponse


class PlaylistTrackResponse(BaseModel):
    position: int
    track: TrackResponse

    model_config = {"from_attributes": True}


class PlaylistResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    playlist_tracks: list[PlaylistTrackResponse] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_duration_ms(self) -> int:
        return sum(pt.track.duration_ms for pt in self.playlist_tracks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def track_count(self) -> int:
        return len(self.playlist_tracks)

    model_config = {"from_attributes": True}
