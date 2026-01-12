import os
from dotenv import load_dotenv

def _load_local_env_if_present():
    """
    In Azure, environment variables are injected by the platform.
    Locally, allow .env.* files for convenience.
    """
    env_name = os.getenv("ENV", "dev").lower()  # dev | prod | test | cloud
    env_file = f".env.{env_name}"

    local_path = os.path.join(os.path.dirname(__file__), env_file)
    if os.path.exists(local_path):
        load_dotenv(dotenv_path=local_path, override=False)

_load_local_env_if_present()

ENV = os.getenv("ENV", "dev").lower()

# --- Core DB ---
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "")

# --- Auth / Secrets ---
SECRET_KEY = os.getenv("SECRET_KEY", "")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "")

ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MIN", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# --- Base URL for share links (important in cloud) ---
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# --- CORS (comma-separated) ---
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]

# --- Storage backend ---
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "azure").lower()  # azure | s3

# Azure Blob
AZURE_USE_EMULATOR = os.getenv("AZURE_USE_EMULATOR", "false").lower() == "true"
AZURE_BLOB_CONN_STR = os.getenv("AZURE_BLOB_CONN_STR", "")
AZURE_CONTAINER_RAW = os.getenv("AZURE_CONTAINER_RAW", "mhd-raw")
AZURE_CONTAINER_PROCESSED = os.getenv("AZURE_CONTAINER_PROCESSED", "mhd-processed")

# S3/Minio (optional)
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET_RAW = os.getenv("S3_BUCKET_RAW", "mhd-raw")
S3_BUCKET_PROCESSED = os.getenv("S3_BUCKET_PROCESSED", "mhd-processed")
