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
