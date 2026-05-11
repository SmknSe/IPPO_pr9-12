from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SERVICE_DIR = Path(__file__).resolve().parents[1] / "services" / "booking_service"
sys.path.insert(0, str(SERVICE_DIR.resolve()))

db_spec = importlib.util.spec_from_file_location("booking_database", SERVICE_DIR / "database.py")
database = importlib.util.module_from_spec(db_spec)
assert db_spec and db_spec.loader
db_spec.loader.exec_module(database)

main_spec = importlib.util.spec_from_file_location("booking_main", SERVICE_DIR / "main.py")
main = importlib.util.module_from_spec(main_spec)
assert main_spec and main_spec.loader
main_spec.loader.exec_module(main)

engine = create_engine("sqlite:///./test_booking.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
database.engine = engine
database.SessionLocal = TestingSessionLocal
main.engine = engine
main.SessionLocal = TestingSessionLocal
main.Base.metadata.drop_all(bind=engine)
main.Base.metadata.create_all(bind=engine)
main.on_startup()
client = TestClient(main.app)


def test_list_rooms_returns_seeded_rooms():
    response = client.get("/rooms")
    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_create_booking_success():
    start = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    end = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    response = client.post(
        "/bookings",
        json={"room_id": 1, "user_email": "alice@example.com", "start_time": start, "end_time": end},
    )
    assert response.status_code == 201
    assert response.json()["room_id"] == 1


def test_create_booking_conflict():
    start = datetime.utcnow() + timedelta(hours=3)
    end = datetime.utcnow() + timedelta(hours=4)
    first = client.post(
        "/bookings",
        json={"room_id": 2, "user_email": "bob@example.com", "start_time": start.isoformat(), "end_time": end.isoformat()},
    )
    assert first.status_code == 201

    second = client.post(
        "/bookings",
        json={
            "room_id": 2,
            "user_email": "eve@example.com",
            "start_time": (start + timedelta(minutes=15)).isoformat(),
            "end_time": (end + timedelta(minutes=15)).isoformat(),
        },
    )
    assert second.status_code == 409


def test_create_room_and_list_bookings_in_range():
    room = client.post("/rooms", json={"name": "Zeta", "capacity": 5})
    assert room.status_code == 201
    room_id = room.json()["id"]

    start = (datetime.utcnow() + timedelta(hours=10)).isoformat()
    end = (datetime.utcnow() + timedelta(hours=11)).isoformat()
    booking = client.post(
        "/bookings",
        json={"room_id": room_id, "user_email": "cal@example.com", "start_time": start, "end_time": end},
    )
    assert booking.status_code == 201

    range_start = (datetime.utcnow() + timedelta(hours=9)).isoformat()
    range_end = (datetime.utcnow() + timedelta(hours=12)).isoformat()
    listed = client.get(
        "/bookings",
        params={"range_start": range_start, "range_end": range_end},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["user_email"] == "cal@example.com"


def test_delete_room_blocked_when_bookings_exist():
    room = client.post("/rooms", json={"name": "Eta", "capacity": 3})
    room_id = room.json()["id"]
    start = (datetime.utcnow() + timedelta(hours=20)).isoformat()
    end = (datetime.utcnow() + timedelta(hours=21)).isoformat()
    client.post(
        "/bookings",
        json={"room_id": room_id, "user_email": "x@example.com", "start_time": start, "end_time": end},
    )
    blocked = client.delete(f"/rooms/{room_id}")
    assert blocked.status_code == 409


def test_delete_room_success_when_empty():
    room = client.post("/rooms", json={"name": "Theta", "capacity": 2})
    room_id = room.json()["id"]
    deleted = client.delete(f"/rooms/{room_id}")
    assert deleted.status_code == 204
    missing = client.delete(f"/rooms/{room_id}")
    assert missing.status_code == 404
