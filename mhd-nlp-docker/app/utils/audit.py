from datetime import datetime, timezone
from typing import Callable, Any, Dict
from functools import wraps
from app.db import db


_events = db["audit_events"]
_events.create_index([("ts", 1)])
_events.create_index([("action", 1)])

def audit(action: str, meta: Dict[str, Any] | None = None):
    """Decorator: write an audit event after the function runs (even on error, we log outcome)."""
    meta = meta or {}
    def _wrap(func: Callable):
        @wraps(func)
        def _inner(*args, **kwargs):
            ok = True
            err = None
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ok, err = False, repr(e)
                raise
            finally:
                try:
                    doc = {
                        "ts": datetime.now(timezone.utc),
                        "action": action,
                        "ok": ok,
                        "err": err,
                        "meta": meta,

                    }
                    _events.insert_one(doc)
                except Exception:
                    pass
        return _inner
    return _wrap
