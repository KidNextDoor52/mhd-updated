# app/utils/logger.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db import db

activity_logs = db["activity_logs"]


def log_activity(user_id: str, action: str, metadata: Optional[dict] = None) -> None:
    """
    Lightweight activity/event log (non-audit).
    """
    activity_logs.insert_one(
        {
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata or {},  # ✅ fixed typo
        }
    )
