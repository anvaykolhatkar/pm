import sqlite3
from pathlib import Path

from app.db import connect_db, initialize_database


def test_initialize_database_creates_file_and_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    created_path = initialize_database(db_path)

    assert created_path.exists()

    with connect_db(created_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }

    expected = {"schema_migrations", "users", "boards", "board_columns", "cards"}
    assert expected.issubset(tables)


def test_foreign_keys_enforced(tmp_path: Path) -> None:
    db_path = tmp_path / "fk.db"
    initialize_database(db_path)

    with connect_db(db_path) as connection:
        # Cannot create a board without an existing user.
        try:
            connection.execute(
                "INSERT INTO boards (user_id, name) VALUES (?, ?)",
                (999, "Invalid board"),
            )
            connection.commit()
            assert False, "Expected foreign key violation"
        except sqlite3.IntegrityError:
            pass

        # Insert a valid user and board.
        connection.execute("INSERT INTO users (username) VALUES (?)", ("user",))
        user_id = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            ("user",),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO boards (user_id, name) VALUES (?, ?)",
            (user_id, "Main Board"),
        )
        board_id = connection.execute(
            "SELECT id FROM boards WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]

        # Cannot create a card with a missing column.
        try:
            connection.execute(
                """
                INSERT INTO cards (board_id, column_id, title, details, position)
                VALUES (?, ?, ?, ?, ?)
                """,
                (board_id, 12345, "Card", "Details", 0),
            )
            connection.commit()
            assert False, "Expected foreign key violation"
        except sqlite3.IntegrityError:
            pass
