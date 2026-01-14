# app/storage/backend.py
from __future__ import annotations

import os
import io
from typing import Optional

BACKEND = os.getenv("STORAGE_BACKEND", "azure").lower()

# -------------------------
# Azure Blob
# -------------------------
AZURE_BLOB_CONN_STR = os.getenv("AZURE_BLOB_CONN_STR", "")
AZURE_CONTAINER_RAW = os.getenv("AZURE_CONTAINER_RAW", "mhd-raw")
AZURE_CONTAINER_PROCESSED = os.getenv("AZURE_CONTAINER_PROCESSED", "mhd-processed")

blob_service = None
ContentSettings = None

# -------------------------
# S3 / MinIO
# -------------------------
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "adminadmin")
S3_BUCKET_RAW = os.getenv("S3_BUCKET_RAW", "mhd-raw")
S3_BUCKET_PROCESSED = os.getenv("S3_BUCKET_PROCESSED", "mhd-processed")

s3 = None


def storage_startup() -> None:
    """
    Initialize storage clients (Azure Blob or S3).
    IMPORTANT: call this from FastAPI startup event.
    """
    global blob_service, ContentSettings, s3

    if BACKEND == "azure":
        from azure.storage.blob import BlobServiceClient, ContentSettings as _ContentSettings

        if not AZURE_BLOB_CONN_STR:
            raise RuntimeError("AZURE_BLOB_CONN_STR not set")

        ContentSettings = _ContentSettings
        blob_service = BlobServiceClient.from_connection_string(AZURE_BLOB_CONN_STR)

    elif BACKEND == "s3":
        from minio import Minio

        # Minio wants host:port (no scheme)
        endpoint = S3_ENDPOINT.replace("http://", "").replace("https://", "").strip("/")

        s3 = Minio(
            endpoint=endpoint,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            secure=S3_ENDPOINT.startswith("https"),
        )
    else:
        raise RuntimeError(f"Unknown STORAGE_BACKEND: {BACKEND}")


# -------------------------
# Azure helpers
# -------------------------
def _azure_put(container: str, key: str, data: bytes, content_type: Optional[str] = None):
    if blob_service is None:
        raise RuntimeError("Azure blob_service not initialized (call storage_startup)")

    bc = blob_service.get_blob_client(container=container, blob=key)

    kwargs = {}
    if content_type and ContentSettings is not None:
        kwargs["content_settings"] = ContentSettings(content_type=content_type)

    bc.upload_blob(data, overwrite=True, **kwargs)


def _azure_get(container: str, key: str) -> bytes:
    if blob_service is None:
        raise RuntimeError("Azure blob_service not initialized (call storage_startup)")

    bc = blob_service.get_blob_client(container=container, blob=key)
    return bc.download_blob().readall()


# -------------------------
# S3 helpers
# -------------------------
def _s3_put(bucket: str, key: str, data: bytes, content_type: Optional[str] = None):
    """
    MinIO put_object requires a file-like object with .read()
    """
    if s3 is None:
        raise RuntimeError("S3 client not initialized (call storage_startup)")

    stream = io.BytesIO(data)
    s3.put_object(
        bucket_name=bucket,
        object_name=key,
        data=stream,
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )


def _s3_get(bucket: str, key: str) -> bytes:
    if s3 is None:
        raise RuntimeError("S3 client not initialized (call storage_startup)")

    resp = s3.get_object(bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def ensure_buckets():
    """
    Create containers/buckets used by the app + MLflow artifacts.
    Call this on application startup (not on import).
    """
    if BACKEND == "s3":
        for b in (S3_BUCKET_RAW, S3_BUCKET_PROCESSED, "mhd-mlflow-artifacts"):
            if not s3.bucket_exists(b):
                s3.make_bucket(b)
    else:
        if blob_service is None:
            raise RuntimeError("Azure blob_service not initialized (call storage_startup)")

        for c in (AZURE_CONTAINER_RAW, AZURE_CONTAINER_PROCESSED, "mhd-mlflow-artifacts"):
            try:
                blob_service.create_container(c)
            except Exception:
                # container already exists
                pass


# -------------------------
# Public API (used by app)
# -------------------------
def put_raw(key: str, data: bytes, content_type: Optional[str] = None):
    if BACKEND == "s3":
        return _s3_put(S3_BUCKET_RAW, key, data, content_type)
    return _azure_put(AZURE_CONTAINER_RAW, key, data, content_type)


def put_processed(key: str, data: bytes, content_type: Optional[str] = None):
    if BACKEND == "s3":
        return _s3_put(S3_BUCKET_PROCESSED, key, data, content_type)
    return _azure_put(AZURE_CONTAINER_PROCESSED, key, data, content_type)


def get_bytes_raw(key: str) -> bytes:
    if BACKEND == "s3":
        return _s3_get(S3_BUCKET_RAW, key)
    return _azure_get(AZURE_CONTAINER_RAW, key)


def get_bytes_processed(key: str) -> bytes:
    if BACKEND == "s3":
        return _s3_get(S3_BUCKET_PROCESSED, key)
    return _azure_get(AZURE_CONTAINER_PROCESSED, key)


# backwards compatibility
def get_bytes(key: str) -> bytes:
    return get_bytes_raw(key)
