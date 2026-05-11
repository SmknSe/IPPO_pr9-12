import importlib.util
from pathlib import Path
import sys

from fastapi.testclient import TestClient

GATEWAY_DIR = Path(__file__).resolve().parents[1] / "services" / "gateway"
sys.path.insert(0, str(GATEWAY_DIR.resolve()))

spec = importlib.util.spec_from_file_location("gateway_main", GATEWAY_DIR / "main.py")
main = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(main)


class MockResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None, headers=None):
        if "/bookings" in url:
            return MockResponse(200, [])
        if "/auth/me" in url:
            return MockResponse(200, {"email": "a@a.com", "is_admin": False})
        return MockResponse(200, [{"id": 1, "name": "Alpha", "capacity": 6}])

    async def post(self, url, json=None, headers=None):
        if "/auth/register" in url or "/auth/login" in url:
            return MockResponse(
                201 if "/register" in url else 200,
                {
                    "access_token": "fake",
                    "token_type": "bearer",
                    "user": {"email": (json or {}).get("email", "user@x.com"), "is_admin": False},
                },
            )
        if url.rstrip("/").endswith("/rooms"):
            return MockResponse(201, {"id": 3, **(json or {})})
        return MockResponse(201, {"id": 1, "room_id": 1, "user_id": 1, "user_email": "t@t.com", **(json or {})})

    async def patch(self, url, json=None, headers=None):
        payload = json or {}
        return MockResponse(200, {"id": 1, "name": payload.get("name", "Alpha"), "capacity": payload.get("capacity", 6)})

    async def delete(self, url, headers=None):
        return MockResponse(204, None)


def test_gateway_proxy_endpoints(monkeypatch):
    monkeypatch.setattr(main.httpx, "AsyncClient", DummyClient)
    client = TestClient(main.app)

    rooms = client.get("/api/rooms")
    assert rooms.status_code == 200
    assert rooms.json()[0]["name"] == "Alpha"

    reg = client.post("/api/auth/register", json={"email": "u@u.com", "password": "longenough"})
    assert reg.status_code == 200
    assert reg.json()["access_token"] == "fake"

    me = client.get("/api/auth/me", headers={"Authorization": "Bearer fake"})
    assert me.status_code == 200
    assert me.json()["email"] == "a@a.com"

    booking = client.post(
        "/api/bookings",
        headers={"Authorization": "Bearer t"},
        json={
            "room_id": 1,
            "start_time": "2026-05-12T10:00:00",
            "end_time": "2026-05-12T11:00:00",
        },
    )
    assert booking.status_code == 200
    assert booking.json()["room_id"] == 1

    bookings = client.get(
        "/api/bookings",
        headers={"Authorization": "Bearer t"},
        params={"range_start": "2026-05-01T00:00:00Z", "range_end": "2026-05-31T23:59:59Z"},
    )
    assert bookings.status_code == 200
    assert bookings.json() == []

    created_room = client.post(
        "/api/rooms",
        headers={"Authorization": "Bearer admin"},
        json={"name": "Delta", "capacity": 8},
    )
    assert created_room.status_code == 200
    assert created_room.json()["name"] == "Delta"

    patched = client.patch(
        "/api/rooms/1",
        headers={"Authorization": "Bearer admin"},
        json={"capacity": 12},
    )
    assert patched.status_code == 200
    assert patched.json()["capacity"] == 12

    deleted = client.delete("/api/rooms/1", headers={"Authorization": "Bearer admin"})
    assert deleted.status_code == 204
