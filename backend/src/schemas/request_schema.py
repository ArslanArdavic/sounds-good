import uuid

from pydantic import BaseModel, Field


class GeneratePlaylistRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language description of the desired playlist.",
        examples=["An hour of jazzy Sunday morning music, around 60 minutes"],
    )


class SaveToSpotifyRequest(BaseModel):
    playlist_id: uuid.UUID
    name: str | None = Field(
        default=None,
        max_length=255,
        description="Custom name for the Spotify playlist. Defaults to the generated name.",
    )
