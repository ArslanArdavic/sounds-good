from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    secret_key: str
    encryption_key: str

    # Database
    database_url: str = "sqlite:///./sounds_good.db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # ChromaDB (default 8001 — backend API uses 8000; HttpClient must reach real Chroma)
    chromadb_host: str = "localhost"
    chromadb_port: int = 8001

    # Vector search
    vector_search_default_n: int = 1000
    vector_search_max_distance: float | None = None

    # Spotify API
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://localhost:3000/callback"

    # Groq API (LLM playlist generation)
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    groq_request_timeout_s: float = 90.0
    groq_http_max_retries: int = 3
    # Keep prompts under Groq on-demand TPM/context limits (~12k tokens typical tier).
    playlist_generation_max_candidates: int = 80
    # Hard cap on the candidate-list block (chars); extra safety vs long track titles.
    playlist_generation_max_candidate_chars: int = 22000
    playlist_generation_max_attempts: int = 2
    duration_tolerance_minutes: int = 15
    default_target_duration_minutes: int = 45

    # CORS — must be a JSON array in .env: ["http://localhost:3000"]
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # allow HF_TOKEN and other tooling vars in .env
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
