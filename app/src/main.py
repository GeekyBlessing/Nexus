import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

VERSION = os.getenv("APP_VERSION", "dev")

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency", ["path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
INFO = Gauge("app_info", "Build info", ["version"])
INFO.labels(VERSION).set(1)

app = FastAPI(title="nexus-app", version=VERSION)


@app.middleware("http")
async def instrument(request: Request, call_next):
    start = time.perf_counter()
    path = request.url.path
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        if path != "/metrics":
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(path).observe(time.perf_counter() - start)


@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}


@app.get("/api/orders")
def orders():
    return {"version": VERSION, "orders": [{"id": 1, "total": 42.50}]}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)