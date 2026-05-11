import time
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import and_, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import Booking, Room
from schemas import BookingCreate, BookingOut, RoomCreate, RoomOut, RoomUpdate

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


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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


@app.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db)):
    room = Room(name=payload.name.strip(), capacity=payload.capacity)
    db.add(room)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="room name already exists") from None
    db.refresh(room)
    return room


@app.patch("/rooms/{room_id}", response_model=RoomOut)
def update_room(room_id: int, payload: RoomUpdate, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    if payload.name is not None:
        room.name = payload.name.strip()
    if payload.capacity is not None:
        room.capacity = payload.capacity
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="room name already exists") from None
    db.refresh(room)
    return room


@app.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    has_bookings = db.scalar(select(exists().where(Booking.room_id == room_id)))
    if has_bookings:
        raise HTTPException(status_code=409, detail="cannot delete room with existing bookings")
    db.delete(room)
    db.commit()


@app.get("/bookings", response_model=list[BookingOut])
def list_bookings(
    range_start: datetime = Query(..., description="Start of the visible window (ISO-8601)"),
    range_end: datetime = Query(..., description="End of the visible window (ISO-8601)"),
    room_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    rs = _ensure_utc(range_start)
    re = _ensure_utc(range_end)
    if re <= rs:
        raise HTTPException(status_code=400, detail="range_end must be greater than range_start")
    stmt = select(Booking).where(
        Booking.start_time < re,
        Booking.end_time > rs,
    )
    if room_id is not None:
        stmt = stmt.where(Booking.room_id == room_id)
    return db.scalars(stmt.order_by(Booking.start_time)).all()


@app.post("/bookings", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    start_time = _ensure_utc(payload.start_time)
    end_time = _ensure_utc(payload.end_time)
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be greater than start_time")
    if start_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="start_time must be in the future")

    room_exists = db.scalar(select(exists().where(Room.id == payload.room_id)))
    if not room_exists:
        raise HTTPException(status_code=404, detail="room not found")

    conflict_stmt = select(
        exists().where(
            and_(
                Booking.room_id == payload.room_id,
                Booking.start_time < end_time,
                Booking.end_time > start_time,
            )
        )
    )
    if db.scalar(conflict_stmt):
        raise HTTPException(status_code=409, detail="time slot is already occupied")

    booking = Booking(
        room_id=payload.room_id,
        user_email=payload.user_email.strip(),
        start_time=start_time,
        end_time=end_time,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    BOOKINGS_CREATED.inc()
    return booking
