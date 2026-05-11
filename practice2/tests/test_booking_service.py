import os
from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import sys

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-pytest")
os.environ.setdefault("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "admin123")
os.environ["DATABASE_URL"] = "sqlite:///./test_booking.db"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SERVICE_DIR = Path(__file__).resolve().parents[1] / "services" / "booking_service"
sys.path.insert(0, str(SERVICE_DIR.resolve()))

db_spec = importlib.util.spec_from_file_location("database", SERVICE_DIR / "database.py")
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
main.Base.metadata.drop_all(bind=engine)
main.Base.metadata.create_all(bind=engine)
main.on_startup()
client = TestClient(main.app)

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(email: str, password: str) -> dict[str, str]:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return _headers(r.json()["access_token"])


def _register(email: str, password: str) -> dict[str, str]:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return _headers(r.json()["access_token"])


def test_list_rooms_returns_seeded_rooms():
    response = client.get("/rooms")
    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_create_booking_success():
    hdr = _register("alice@example.com", "secret12")
    start = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    end = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    response = client.post(
        "/bookings",
        json={"room_id": 1, "start_time": start, "end_time": end},
        headers=hdr,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["room_id"] == 1
    assert body["user_email"] == "alice@example.com"
    assert body["user_id"] >= 1


def test_create_booking_conflict():
    hdr = _register("bob@example.com", "secret12")
    start = datetime.utcnow() + timedelta(hours=3)
    end = datetime.utcnow() + timedelta(hours=4)
    first = client.post(
        "/bookings",
        json={"room_id": 2, "start_time": start.isoformat(), "end_time": end.isoformat()},
        headers=hdr,
    )
    assert first.status_code == 201

    second = client.post(
        "/bookings",
        json={
            "room_id": 2,
            "start_time": (start + timedelta(minutes=15)).isoformat(),
            "end_time": (end + timedelta(minutes=15)).isoformat(),
        },
        headers=hdr,
    )
    assert second.status_code == 409


def test_create_room_and_list_bookings_in_range():
    admin_h = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    room = client.post("/rooms", json={"name": "Zeta", "capacity": 5}, headers=admin_h)
    assert room.status_code == 201
    room_id = room.json()["id"]

    user_h = _register("cal@example.com", "secret12")
    start = (datetime.utcnow() + timedelta(hours=10)).isoformat()
    end = (datetime.utcnow() + timedelta(hours=11)).isoformat()
    booking = client.post(
        "/bookings",
        json={"room_id": room_id, "start_time": start, "end_time": end},
        headers=user_h,
    )
    assert booking.status_code == 201

    range_start = (datetime.utcnow() + timedelta(hours=9)).isoformat()
    range_end = (datetime.utcnow() + timedelta(hours=12)).isoformat()
    listed = client.get(
        "/bookings",
        params={"range_start": range_start, "range_end": range_end},
        headers=user_h,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["user_email"] == "cal@example.com"


def test_delete_room_blocked_when_bookings_exist():
    admin_h = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    room = client.post("/rooms", json={"name": "Eta", "capacity": 3}, headers=admin_h)
    room_id = room.json()["id"]
    user_h = _register("roomlock@example.com", "secret12")
    start = (datetime.utcnow() + timedelta(hours=20)).isoformat()
    end = (datetime.utcnow() + timedelta(hours=21)).isoformat()
    client.post(
        "/bookings",
        json={"room_id": room_id, "start_time": start, "end_time": end},
        headers=user_h,
    )
    blocked = client.delete(f"/rooms/{room_id}", headers=admin_h)
    assert blocked.status_code == 409


def test_delete_room_success_when_empty():
    admin_h = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    room = client.post("/rooms", json={"name": "Theta", "capacity": 2}, headers=admin_h)
    room_id = room.json()["id"]
    deleted = client.delete(f"/rooms/{room_id}", headers=admin_h)
    assert deleted.status_code == 204
    missing = client.delete(f"/rooms/{room_id}", headers=admin_h)
    assert missing.status_code == 404


def test_room_mutations_require_admin():
    user_h = _register("noroom@example.com", "secret12")
    assert client.post("/rooms", json={"name": "X1", "capacity": 1}, headers=user_h).status_code == 403
    assert client.patch("/rooms/1", json={"capacity": 99}, headers=user_h).status_code == 403
    assert client.delete("/rooms/1", headers=user_h).status_code == 403


def test_bookings_require_auth():
    r = client.get(
        "/bookings",
        params={
            "range_start": "2026-01-01T00:00:00",
            "range_end": "2026-12-31T23:59:59",
        },
    )
    assert r.status_code == 401
