import json
import logging
import time
from collections import Counter
from threading import Lock
from uuid import uuid4
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.db.database import SessionLocal

logger = logging.getLogger("uvicorn.error")

def install_observability(app):
    counts = Counter()
    lock = Lock()

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        return JSONResponse(status_code=422, content={"detail": "Invalid request data"})

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = uuid4().hex
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
                logger.error(json.dumps({
                    "request_id": request_id,
                    "method": request.method,
                    "error_type": type(exc).__name__,
                }))
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error"},
                )
        elapsed = round((time.perf_counter()-start)*1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        with lock:
            counts["requests"] += 1
            counts["errors"] += int(response.status_code >= 500)
            counts["latency_ms"] += elapsed
        logger.info(json.dumps({"request_id":request_id,"method":request.method,"status":response.status_code,"duration_ms":elapsed}))
        return response

    @app.get("/health/live", include_in_schema=False)
    def live():
        return {"status":"alive"}

    @app.get("/health/ready", include_in_schema=False)
    def ready():
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            return {"status":"ready"}
        except Exception:
            return JSONResponse(status_code=503, content={"status":"unavailable"})

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        with lock:
            n = counts["requests"]
            return {"requests":n,"errors":counts["errors"],"mean_latency_ms":round(counts["latency_ms"]/max(n,1),2),"error_rate":counts["errors"]/max(n,1)}
