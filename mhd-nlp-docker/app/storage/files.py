# app/storage/files.py
from __future__ import annotations

from typing import Optional

from app.storage.backend import put_raw, get_bytes_raw


def save_upload(storage_key: str, data: bytes, content_type: Optional[str] = None) -> str:
    """
    Store file in the configured backend and return the storage_key.
    """
    put_raw(storage_key, data, content_type=content_type)
    return storage_key


def load_upload(storage_key: str) -> bytes:
    return get_bytes_raw(storage_key)
