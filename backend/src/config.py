from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


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

    # ChromaDB
    chromadb_host: str = "localhost"
    chromadb_port: int = 8000

    # Spotify API
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://localhost:3000/callback"

    # Groq API
    groq_api_key: str

    # CORS — must be a JSON array in .env: ["http://localhost:3000"]
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()
