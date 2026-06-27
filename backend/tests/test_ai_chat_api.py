import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.main as main_module
from app.db import initialize_database
from app.main import SESSIONS, app

client = TestClient(app)


def setup_db(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "ai-chat.db"
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


def test_ai_chat_without_board_update(tmp_path: Path, monkeypatch) -> None:
    setup_db(tmp_path, monkeypatch)
    login()

    monkeypatch.setattr(
        main_module,
        "run_ai_chat_prompt",
        lambda _prompt: json.dumps({"response": "No changes", "board_update": None}),
    )
    response = client.post(
        "/api/ai/chat",
        json={
            "question": "What should I do next?",
            "history": [{"role": "user", "content": "Hello"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "No changes"
    assert body["board_updated"] is False
    assert len(body["board"]["columns"]) == 5


def test_ai_chat_with_board_update(tmp_path: Path, monkeypatch) -> None:
    setup_db(tmp_path, monkeypatch)
    login()

    monkeypatch.setattr(
        main_module,
        "run_ai_chat_prompt",
        lambda _prompt: json.dumps(
            {
                "response": "Renamed backlog to Ideas.",
                "board_update": [
                    {
                        "action": "rename_column",
                        "column_id": "col-1",
                        "title": "Ideas",
                    }
                ],
            }
        ),
    )
    response = client.post(
        "/api/ai/chat",
        json={"question": "Rename Backlog to Ideas", "history": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["board_updated"] is True
    assert body["board"]["columns"][0]["title"] == "Ideas"
