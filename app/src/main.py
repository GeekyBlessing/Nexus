import os
import random
import threading
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

VERSION = os.getenv("APP_VERSION", "dev")
CHAOS = os.getenv("CHAOS_ENABLED", "false").lower() == "true"

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency", ["path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
INFO = Gauge("app_info", "Build info", ["version"])
INFO.labels(VERSION).set(1)


class State:
    healthy = True
    error_rate = float(os.getenv("FAULT_ERROR_RATE", "0"))
    extra_latency = 0.0
    leak: list[bytes] = []


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
    if not State.healthy:
        raise HTTPException(503, "unhealthy")
    return {"status": "ok", "version": VERSION}


@app.get("/api/orders")
def orders():
    if State.extra_latency:
        time.sleep(State.extra_latency)
    if random.random() < State.error_rate:
        raise HTTPException(500, "simulated failure")
    return {"version": VERSION, "orders": [{"id": 1, "total": 42.50}]}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if CHAOS:

    @app.post("/chaos/crash")
    def crash():
        threading.Timer(0.2, lambda: os._exit(1)).start()
        return {"chaos": "crashing"}

    @app.post("/chaos/unhealthy")
    def unhealthy():
        State.healthy = False
        return {"chaos": "health check now failing"}

    @app.post("/chaos/errors")
    def errors(rate: float = 0.5):
        State.error_rate = max(0.0, min(rate, 1.0))
        return {"chaos": f"error rate {State.error_rate}"}

    @app.post("/chaos/latency")
    def latency(seconds: float = 1.5):
        State.extra_latency = max(0.0, min(seconds, 10.0))
        return {"chaos": f"added {State.extra_latency}s latency"}

    @app.post("/chaos/memory")
    def memory(mb: int = 100):
        State.leak.append(b"x" * mb * 1024 * 1024)
        return {"chaos": f"leaked {mb}MB"}