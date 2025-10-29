import os
from typing import Optional

BACKEND = os.getenv("STORAGE_BACKEND", "azure").lower()

# azure blob (azurite or real azure)

AZURE_BLOB_CONN_STR = os.getenv("AZURE_BLOB_CONN_STR", "")
AZURE_CONTAINER_RAW = os.getenv("AZURE_CONTAINER_RAW", "mhd-raw")
AZURE_CONTAINER_PROCESSED = os.getenv("AZURE_CONTAINER_PROCESSED", "mhd-processed")

blob_service = None
if BACKEND == "azure":
    from azure.storage.blob import BlobServiceClient
    if not AZURE_BLOB_CONN_STR:
        raise RuntimeError("AZURE_BLOB_CONN_STR not set")
    blob_service = BlobServiceClient.from_connection_string(AZURE_BLOB_CONN_STR)

def _azure_put(container: str, key: str, data: bytes, content_type: Optional[str] = None):
    bc = blob_service.get_blob_client(container=container, blob=key)
    bc.upload_blob(data, overwrite=True)

# S3 / Minio (local or real S3)
S3_ENDPOINT =  os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "adminadmin")
S3_BUCKET_RAW = os.getenv("S3_BUCKET_RAW", "mhd-raw")
S3_BUCKET_PROCESSED = os.getenv("S3_BUCKET_PROCESSED", "mhd-processed")

s3 = None
if BACKEND == "s3":
    from minio import Minio
    s3 = Minio(
        endpoint=S3_ENDPOINT.replace("http://", "").replace("https://", ""),
        access_key=S3_ACCESS_KEY,
        secret_key=S3_SECRET_KEY,
        secure=S3_ENDPOINT.startswith("https"),
    )

def _s3_put(bucket: str, key: str, data: bytes, content_type: Optional[str] = None):
    s3.put_object(
        bucket_name=bucket,
        object_name=key,
        data=data,
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )

def ensure_buckets():
    """Create containers/buckets used by the app + MLflow artifacts."""
    if BACKEND == "s3":
        for b in (S3_BUCKET_RAW, S3_BUCKET_PROCESSED, "mhd-mlflow-artifacts"):
            if not s3.bucket_exists(b):
                s3.make_bucket(b)
    else:
        for c in (AZURE_CONTAINER_RAW, AZURE_CONTAINER_PROCESSED, "mhd-mlflow-artifacts"):
            try:
                blob_service.create_container(c)
            except Exception:
                pass  # already exists

def put_raw(key: str, data: bytes, content_type: Optional[str] = None):
    if BACKEND == "s3":
        return _s3_put(S3_BUCKET_RAW, key, data, content_type)
    return _azure_put(AZURE_CONTAINER_RAW, key, data, content_type)

def put_processed(key: str, data: bytes, content_type: Optional[str] = None):
    if BACKEND == "s3":
        return _s3_put(S3_BUCKET_PROCESSED, key, data, content_type)
    return _azure_put(AZURE_CONTAINER_PROCESSED, key, data, content_type)