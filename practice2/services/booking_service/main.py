import time
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import and_, exists, select
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import Booking, Room
from schemas import BookingCreate, BookingOut, RoomOut

REQUEST_COUNTER = Counter(
    "booking_http_requests_total",
    "Total HTTP requests handled by booking service",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "booking_http_request_duration_seconds",
    "HTTP request latency in booking service",
    ["method", "path"],
)
BOOKINGS_CREATED = Counter(
    "bookings_created_total",
    "Total successful room bookings",
)

app = FastAPI(title="Meeting Rooms Booking Service", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(exists().where(Room.id == 1))):
            return
        db.add_all([Room(name="Alpha", capacity=6), Room(name="Beta", capacity=10), Room(name="Gamma", capacity=4)])
        db.commit()


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
    return {"status": "ok", "service": "booking-service"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/rooms", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.scalars(select(Room).order_by(Room.id)).all()


@app.post("/bookings", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be greater than start_time")
    if payload.start_time < datetime.utcnow():
        raise HTTPException(status_code=400, detail="start_time must be in the future")

    room_exists = db.scalar(select(exists().where(Room.id == payload.room_id)))
    if not room_exists:
        raise HTTPException(status_code=404, detail="room not found")

    conflict_stmt = select(
        exists().where(
            and_(
                Booking.room_id == payload.room_id,
                Booking.start_time < payload.end_time,
                Booking.end_time > payload.start_time,
            )
        )
    )
    if db.scalar(conflict_stmt):
        raise HTTPException(status_code=409, detail="time slot is already occupied")

    booking = Booking(**payload.model_dump())
    db.add(booking)
    db.commit()
    db.refresh(booking)
    BOOKINGS_CREATED.inc()
    return booking
