import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import SESSIONS, app

client = TestClient(app)


def test_root_requires_auth() -> None:
    SESSIONS.clear()
    response = client.get("/")
    assert response.status_code == 200
    assert "Sign in" in response.text


def test_login_accepts_valid_credentials() -> None:
    SESSIONS.clear()
    response = client.post(
        "/api/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "pm_session" in response.cookies


def test_login_rejects_invalid_credentials() -> None:
    SESSIONS.clear()
    response = client.post(
        "/api/login",
        json={"username": "user", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_health_route() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "pm-backend"}


def test_logout_invalidates_session() -> None:
    SESSIONS.clear()
    login_response = client.post(
        "/api/login",
        json={"username": "user", "password": "password"},
    )
    assert login_response.status_code == 200

    protected_response = client.get("/")
    assert protected_response.status_code == 200
    assert (
        "Kanban Studio" in protected_response.text
        or "Hello from FastAPI" in protected_response.text
    )

    logout_response = client.post("/api/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "ok"}

    after_logout = client.get("/")
    assert after_logout.status_code == 200
    assert "Sign in" in after_logout.text
