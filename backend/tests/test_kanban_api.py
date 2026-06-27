import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db import initialize_database
from app.main import SESSIONS, app

client = TestClient(app)


def setup_db(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "kanban-test.db"
    monkeypatch.setenv("PM_DB_PATH", str(db_path))
    initialize_database(db_path)
    SESSIONS.clear()
    client.cookies.clear()


def login() -> None:
    response = client.post(
        "/api/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_board_requires_auth() -> None:
    SESSIONS.clear()
    client.cookies.clear()
    response = client.get("/api/board")
    assert response.status_code == 401


def test_board_fetch_and_mutation_flow(tmp_path: Path, monkeypatch) -> None:
    setup_db(tmp_path, monkeypatch)
    login()

    board_response = client.get("/api/board")
    assert board_response.status_code == 200
    board = board_response.json()
    assert len(board["columns"]) == 5
    assert len(board["cards"]) >= 8

    first_column = board["columns"][0]["id"]
    second_column = board["columns"][1]["id"]
    first_card = board["columns"][0]["cardIds"][0]

    rename_response = client.patch(
        f"/api/columns/{first_column}",
        json={"title": "Ideas"},
    )
    assert rename_response.status_code == 200

    add_response = client.post(
        f"/api/columns/{second_column}/cards",
        json={"title": "API-added card", "details": "created in test"},
    )
    assert add_response.status_code == 200
    added_card = add_response.json()["card_id"]

    move_response = client.post(
        f"/api/cards/{first_card}/move",
        json={"target_column_id": second_column},
    )
    assert move_response.status_code == 200

    delete_response = client.delete(f"/api/cards/{added_card}")
    assert delete_response.status_code == 200

    final_board = client.get("/api/board").json()
    assert final_board["columns"][0]["title"] == "Ideas"
    assert first_card in final_board["columns"][1]["cardIds"]
    assert added_card not in final_board["cards"]
