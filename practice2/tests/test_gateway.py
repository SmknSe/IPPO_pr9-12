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

    async def get(self, url, params=None):
        if "/bookings" in url:
            return MockResponse(200, [])
        return MockResponse(200, [{"id": 1, "name": "Alpha", "capacity": 6}])

    async def post(self, url, json=None):
        if url.rstrip("/").endswith("/rooms"):
            return MockResponse(201, {"id": 3, **(json or {})})
        return MockResponse(201, {"id": 1, **(json or {})})

    async def patch(self, url, json=None):
        payload = json or {}
        return MockResponse(200, {"id": 1, "name": payload.get("name", "Alpha"), "capacity": payload.get("capacity", 6)})

    async def delete(self, url):
        return MockResponse(204, None)


def test_gateway_proxy_endpoints(monkeypatch):
    monkeypatch.setattr(main.httpx, "AsyncClient", DummyClient)
    client = TestClient(main.app)

    rooms = client.get("/api/rooms")
    assert rooms.status_code == 200
    assert rooms.json()[0]["name"] == "Alpha"

    booking = client.post(
        "/api/bookings",
        json={
            "room_id": 1,
            "user_email": "test@example.com",
            "start_time": "2026-05-12T10:00:00",
            "end_time": "2026-05-12T11:00:00",
        },
    )
    assert booking.status_code == 200
    assert booking.json()["room_id"] == 1

    bookings = client.get(
        "/api/bookings",
        params={"range_start": "2026-05-01T00:00:00Z", "range_end": "2026-05-31T23:59:59Z"},
    )
    assert bookings.status_code == 200
    assert bookings.json() == []

    created_room = client.post("/api/rooms", json={"name": "Delta", "capacity": 8})
    assert created_room.status_code == 200
    assert created_room.json()["name"] == "Delta"

    patched = client.patch("/api/rooms/1", json={"capacity": 12})
    assert patched.status_code == 200
    assert patched.json()["capacity"] == 12

    deleted = client.delete("/api/rooms/1")
    assert deleted.status_code == 204
