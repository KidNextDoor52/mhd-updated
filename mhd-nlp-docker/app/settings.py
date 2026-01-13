# app/settings.py
from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


def _load_local_env_if_present() -> None:
    """
    In Azure, environment variables are injected by the platform.
    Locally, allow .env.* files for convenience.

    Uses ENV to select one of:
      .env.dev, .env.prod, .env.test, .env.cloud
    """
    env_name = os.getenv("ENV", "dev").lower()
    env_file = f".env.{env_name}"
    local_path = os.path.join(os.path.dirname(__file__), env_file)

    if os.path.exists(local_path):
        load_dotenv(dotenv_path=local_path, override=False)


_load_local_env_if_present()


@dataclass(frozen=True)
class Settings:
    # env
    ENV: str = os.getenv("ENV", "dev").lower()

    # --- Core DB ---
    MONGO_URI: str = os.getenv("MONGO_URI", "")
    MONGO_DB: str = os.getenv("MONGO_DB", "")

    # --- Auth / Secrets ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "")

    ACCESS_TOKEN_EXPIRE_MIN: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MIN", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"

    # --- Base URL for share links ---
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

    # --- CORS (comma-separated) ---
    CORS_ALLOWED_ORIGINS: list[str] = None  # set in __post_init__

    # --- Storage backend ---
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "azure").lower()  # azure | s3

    # Azure Blob
    AZURE_USE_EMULATOR: bool = os.getenv("AZURE_USE_EMULATOR", "false").lower() == "true"
    AZURE_BLOB_CONN_STR: str = os.getenv("AZURE_BLOB_CONN_STR", "")
    AZURE_CONTAINER_RAW: str = os.getenv("AZURE_CONTAINER_RAW", "mhd-raw")
    AZURE_CONTAINER_PROCESSED: str = os.getenv("AZURE_CONTAINER_PROCESSED", "mhd-processed")

    # S3/Minio (optional)
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "")
    S3_BUCKET_RAW: str = os.getenv("S3_BUCKET_RAW", "mhd-raw")
    S3_BUCKET_PROCESSED: str = os.getenv("S3_BUCKET_PROCESSED", "mhd-processed")

    # --- JWT compatibility layer (what middleware expects) ---
    JWT_SECRET: str = None  # set in __post_init__
    JWT_ALG: str = os.getenv("JWT_ALG", "HS256")

    def __post_init__(self) -> None:
        # Parse CORS origins
        cors = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
        object.__setattr__(self, "CORS_ALLOWED_ORIGINS", cors)

        # JWT secret defaults to SECRET_KEY for backward compatibility
        jwt_secret = os.getenv("JWT_SECRET", self.SECRET_KEY)
        object.__setattr__(self, "JWT_SECRET", jwt_secret)


settings = Settings()
__all__ = ["Settings", "settings"]
