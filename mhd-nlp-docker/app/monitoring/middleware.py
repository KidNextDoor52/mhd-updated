import time
import datetime as dt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.db import db

metrics = db["api_metrics"]
metrics.create_index("ts")


class APIMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            try:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                metrics.insert_one(
                    {
                        "ts": dt.datetime.utcnow(),
                        "path": request.url.path,
                        "method": request.method,
                        "status": int(status_code),
                        "latency_ms": float(latency_ms),
                    }
                )
            except Exception:
                # Doesn't break requests if metrics insert fails
                pass
