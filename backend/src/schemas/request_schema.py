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


class SearchTracksRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language description of the music you want.",
        examples=["upbeat dance music for a party"],
    )
    n_results: int | None = Field(
        default=None,
        ge=1,
        le=5000,
        description="Maximum number of results. Defaults to the server-side setting (1000).",
    )
    max_distance: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Maximum cosine distance (0 = identical, 2 = opposite). Omit for no cap.",
    )


class SaveToSpotifyRequest(BaseModel):
    playlist_id: uuid.UUID
    name: str | None = Field(
        default=None,
        max_length=255,
        description="Custom name for the Spotify playlist. Defaults to the generated name.",
    )
