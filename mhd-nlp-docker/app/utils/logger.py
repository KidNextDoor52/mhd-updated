from app.db import db
from datetime import datetime, timezone

activity_logs = db["activity_logs"]

def log_activity(user_id: str, action: str, metadata: dict | None = None):
    activity_logs.insert_one({
        "user_id": user_id,
        "action": action,
        "timestamp": datetime.now(timezone.utc),
        "metatdata": metadata or {}
    })