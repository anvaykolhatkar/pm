import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import SESSIONS, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_sessions() -> None:
    SESSIONS.clear()
    client.cookies.clear()


def login() -> None:
    response = client.post(
        "/api/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_ai_ping_requires_auth() -> None:
    response = client.post("/api/ai/ping", json={"prompt": "2+2"})
    assert response.status_code == 401


def test_ai_ping_returns_mocked_response(monkeypatch) -> None:
    login()

    monkeypatch.setattr(main_module, "run_ai_ping", lambda _: "4")
    response = client.post("/api/ai/ping", json={"prompt": "2+2"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model"] == "claude-haiku-4-5-20251001"
    assert body["response"] == "4"


def test_ai_ping_handles_missing_key(monkeypatch) -> None:
    login()

    def raise_missing_key(_: str) -> str:
        raise ValueError("ANTHROPIC_API_KEY is not configured")

    monkeypatch.setattr(main_module, "run_ai_ping", raise_missing_key)
    response = client.post("/api/ai/ping", json={"prompt": "2+2"})
    assert response.status_code == 400
