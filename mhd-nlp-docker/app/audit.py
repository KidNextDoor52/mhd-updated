import datetime as dt
from app.db import db

audits = db["audits"]
audits.create_index("ts")


def log_event(user: str, action: str, details: dict | None = None):
    """
    Simple synchronous audit logger using PyMongo.
    Never raises – failures are swallowed so they don't break the app.
    """
    doc = {
        "user": user or "anonymous",
        "action": action,
        "details": details or {},
        "ts": dt.datetime.utcnow(),
    }
    try:
        audits.insert_one(doc)
    except Exception:
        # Do not let audit failures crash requests
        pass
