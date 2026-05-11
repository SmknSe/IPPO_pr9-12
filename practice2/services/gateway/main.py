import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field, model_validator
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

BOOKING_SERVICE_URL = os.getenv("BOOKING_SERVICE_URL", "http://booking-service:8001")


def _upstream_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
        detail = data.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            return "; ".join(str(item) for item in detail)
        if detail is not None:
            return str(detail)
    except Exception:
        pass
    return response.text or "upstream request failed"


def _forward_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    auth = request.headers.get("authorization")
    if auth:
        headers["Authorization"] = auth
    return headers


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


class RegisterBody(BaseModel):
    email: str = Field(min_length=3, max_length=256)
    password: str = Field(min_length=6, max_length=128)


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=256)
    password: str


class BookingCreate(BaseModel):
    room_id: int = Field(gt=0)
    start_time: str
    end_time: str


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    capacity: int = Field(gt=0)


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    capacity: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "RoomUpdate":
        if self.name is None and self.capacity is None:
            raise ValueError("at least one of name, capacity is required")
        return self


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


@app.post("/api/auth/register")
async def register(payload: RegisterBody) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{BOOKING_SERVICE_URL}/auth/register",
                json=payload.model_dump(),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_upstream_detail(response))
    return response.json()


@app.post("/api/auth/login")
async def login(payload: LoginBody) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{BOOKING_SERVICE_URL}/auth/login",
                json=payload.model_dump(),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_upstream_detail(response))
    return response.json()


@app.get("/api/auth/me")
async def me(request: Request) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{BOOKING_SERVICE_URL}/auth/me",
                headers=_forward_headers(request),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_upstream_detail(response))
    return response.json()


@app.get("/api/rooms")
async def list_rooms() -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BOOKING_SERVICE_URL}/rooms")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_upstream_detail(response))
    return response.json()


@app.post("/api/rooms")
async def create_room(request: Request, payload: RoomCreate) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{BOOKING_SERVICE_URL}/rooms",
                json=payload.model_dump(),
                headers=_forward_headers(request),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_upstream_detail(response))
    return response.json()


@app.patch("/api/rooms/{room_id}")
async def update_room(room_id: int, request: Request, payload: RoomUpdate) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.patch(
                f"{BOOKING_SERVICE_URL}/rooms/{room_id}",
                json=payload.model_dump(exclude_unset=True),
                headers=_forward_headers(request),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_upstream_detail(response))
    return response.json()


@app.delete("/api/rooms/{room_id}", status_code=204)
async def delete_room(room_id: int, request: Request) -> Response:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.delete(
                f"{BOOKING_SERVICE_URL}/rooms/{room_id}",
                headers=_forward_headers(request),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_upstream_detail(response))
    return Response(status_code=204)


@app.get("/api/bookings")
async def list_bookings(
    request: Request,
    range_start: str,
    range_end: str,
    room_id: int | None = None,
) -> Any:
    params: dict[str, Any] = {"range_start": range_start, "range_end": range_end}
    if room_id is not None:
        params["room_id"] = room_id
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{BOOKING_SERVICE_URL}/bookings",
                params=params,
                headers=_forward_headers(request),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_upstream_detail(response))
    return response.json()


@app.post("/api/bookings")
async def create_booking(request: Request, payload: BookingCreate) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{BOOKING_SERVICE_URL}/bookings",
                json=payload.model_dump(),
                headers=_forward_headers(request),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"booking service unavailable: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_upstream_detail(response))
    return response.json()
