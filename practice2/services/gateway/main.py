import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

BOOKING_SERVICE_URL = os.getenv("BOOKING_SERVICE_URL", "http://booking-service:8001")

REQUEST_COUNTER = Counter(
    "gateway_http_requests_total",
    "Total HTTP requests handled by gateway",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "gateway_http_request_duration_seconds",
    "HTTP request latency in gateway",
    ["method", "path"],
)


class BookingCreate(BaseModel):
    room_id: int = Field(gt=0)
    user_email: str
    start_time: str
    end_time: str


app = FastAPI(title="Meeting Rooms API Gateway", version="1.0.0")


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    REQUEST_COUNTER.labels(request.method, request.url.path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gateway"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/rooms")
async def list_rooms() -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BOOKING_SERVICE_URL}/rooms")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.post("/api/bookings")
async def create_booking(payload: BookingCreate) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(f"{BOOKING_SERVICE_URL}/bookings", json=payload.model_dump())
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()
