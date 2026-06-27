import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import db


@pytest.fixture
def isolated_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "ops.db"
    monkeypatch.setenv("PM_DB_PATH", str(db_path))
    db.initialize_database(db_path)
    return db_path


def test_rename_add_move_delete_card(isolated_db: Path) -> None:
    board = db.get_board_data("user")
    first_column = board["columns"][0]["id"]
    second_column = board["columns"][1]["id"]
    first_card = board["columns"][0]["cardIds"][0]

    db.rename_column("user", int(first_column.removeprefix("col-")), "Ideas")
    added = db.add_card("user", int(second_column.removeprefix("col-")), "New", "Card")
    db.move_card(
        "user",
        int(first_card.removeprefix("card-")),
        int(second_column.removeprefix("col-")),
        None,
    )
    db.delete_card("user", int(added.removeprefix("card-")))

    updated = db.get_board_data("user")
    assert updated["columns"][0]["title"] == "Ideas"
    assert first_card in updated["columns"][1]["cardIds"]
    assert added not in updated["cards"]
