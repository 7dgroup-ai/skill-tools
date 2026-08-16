"""FastAPI 入口：sketch-store 电商链路被测应用。
运行：uvicorn app.main:app --port 8000  （或 docker-compose up -d / make up）
"""
import time

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from . import metrics
from .db import init_db
from .routes import cart, goods, order, user

app = FastAPI(title="sketch-store", version="1.0.0", description="轻量版电商链路被测应用（8 步业务链路）")

app.include_router(user.router)
app.include_router(goods.router)
app.include_router(cart.router)
app.include_router(order.router)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    dur_ms = (time.perf_counter() - start) * 1000
    metrics.record_request(request.method, request.url.path, response.status_code, dur_ms)
    return response


@app.on_event("startup")
def _startup():
    init_db()
    from . import seeded
    seeded.seed("local")


@app.get("/health", tags=["ops"])
def health():
    return {"status": "UP", "app": "sketch-store"}


@app.get("/metrics", response_class=PlainTextResponse, tags=["ops"])
def prom_metrics():
    return PlainTextResponse(metrics.render())


@app.get("/", tags=["ops"])
def root():
    return {"name": "sketch-store", "docs": "/docs", "health": "/health", "metrics": "/metrics"}