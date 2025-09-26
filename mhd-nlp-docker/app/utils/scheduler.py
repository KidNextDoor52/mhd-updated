import threading
import time
from typing import Optional
from app.db import db

# We avoid importing app.services.sync at module import time.
# We'll import inside the worker thread to prevent circular imports.

def _job_loop(interval_seconds: int = 24*60*60):
    # Lazy import here
    from app.services.sync import rebuild_clinical_snapshot, run_risk_rules

    while True:
        for u in db.users.find({}, {"username": 1}):
            user = u["username"]
            try:
                rebuild_clinical_snapshot(user)
                run_risk_rules(user)
            except Exception:
                # Swallow per-user failure to keep the loop going
                pass
        time.sleep(interval_seconds)

def start_background_scheduler(interval_seconds: int = 24*60*60) -> threading.Thread:
    """
    Starts a daemon thread that periodically rebuilds snapshots & rules for all users.
    Returns the thread so you can keep a handle in app.state if desired.
    """
    t = threading.Thread(target=_job_loop, kwargs={"interval_seconds": interval_seconds}, daemon=True)
    t.start()
    return t
