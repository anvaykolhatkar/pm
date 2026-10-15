import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1


def get_db_path() -> Path:
    configured = os.getenv("PM_DB_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent / "data" / "pm.db"


def connect_db(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database(db_path: Path | None = None) -> Path:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with connect_db(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT,
                UNIQUE(user_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS board_columns (
                id INTEGER PRIMARY KEY,
                board_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                position INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT,
                UNIQUE(board_id, position),
                FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY,
                board_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                position INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT,
                UNIQUE(column_id, position),
                FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
                FOREIGN KEY (column_id) REFERENCES board_columns(id) ON DELETE CASCADE
            );
            """
        )
        connection.execute(
            """
            INSERT INTO schema_migrations (version)
            VALUES (?)
            ON CONFLICT(version) DO NOTHING;
            """,
            (SCHEMA_VERSION,),
        )
        connection.commit()

    return path


INITIAL_COLUMNS = [
    "Backlog",
    "Discovery",
    "In Progress",
    "Review",
    "Done",
]

INITIAL_CARDS = [
    (
        0,
        "Align roadmap themes",
        "Draft quarterly themes with impact statements and metrics.",
    ),
    (
        0,
        "Gather customer signals",
        "Review support tags, sales notes, and churn feedback.",
    ),
    (1, "Prototype analytics view", "Sketch initial dashboard layout and key drill-downs."),
    (
        2,
        "Refine status language",
        "Standardize column labels and tone across the board.",
    ),
    (2, "Design card layout", "Add hierarchy and spacing for scanning dense lists."),
    (3, "QA micro-interactions", "Verify hover, focus, and loading states."),
    (4, "Ship marketing page", "Final copy approved and asset pack delivered."),
    (4, "Close onboarding sprint", "Document release notes and share internally."),
]


def _ensure_user(connection: sqlite3.Connection, username: str) -> int:
    row = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row:
        return int(row["id"])

    cursor = connection.execute(
        "INSERT INTO users (username) VALUES (?)",
        (username,),
    )
    return int(cursor.lastrowid)


def _ensure_board_for_user(connection: sqlite3.Connection, user_id: int) -> int:
    row = connection.execute(
        "SELECT id FROM boards WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row:
        return int(row["id"])

    cursor = connection.execute(
        "INSERT INTO boards (user_id, name) VALUES (?, ?)",
        (user_id, "Main Board"),
    )
    return int(cursor.lastrowid)


def _seed_board_if_empty(connection: sqlite3.Connection, board_id: int) -> None:
    column_count = connection.execute(
        "SELECT COUNT(*) AS count FROM board_columns WHERE board_id = ?",
        (board_id,),
    ).fetchone()["count"]
    if column_count > 0:
        return

    column_ids: list[int] = []
    for index, title in enumerate(INITIAL_COLUMNS):
        cursor = connection.execute(
            """
            INSERT INTO board_columns (board_id, title, position)
            VALUES (?, ?, ?)
            """,
            (board_id, title, index),
        )
        column_ids.append(int(cursor.lastrowid))

    next_positions = {column_id: 0 for column_id in column_ids}
    for column_index, title, details in INITIAL_CARDS:
        column_id = column_ids[column_index]
        position = next_positions[column_id]
        next_positions[column_id] += 1
        connection.execute(
            """
            INSERT INTO cards (board_id, column_id, title, details, position)
            VALUES (?, ?, ?, ?, ?)
            """,
            (board_id, column_id, title, details, position),
        )


def _ensure_user_board(connection: sqlite3.Connection, username: str) -> int:
    user_id = _ensure_user(connection, username)
    board_id = _ensure_board_for_user(connection, user_id)
    _seed_board_if_empty(connection, board_id)
    return board_id


def ensure_user_board(username: str) -> int:
    initialize_database()
    with connect_db() as connection:
        board_id = _ensure_user_board(connection, username)
        connection.commit()
        return board_id


def get_board_data(username: str) -> dict:
    board_id = ensure_user_board(username)
    with connect_db() as connection:
        column_rows = connection.execute(
            """
            SELECT id, title
            FROM board_columns
            WHERE board_id = ?
            ORDER BY position, id
            """,
            (board_id,),
        ).fetchall()
        card_rows = connection.execute(
            """
            SELECT id, column_id, title, details
            FROM cards
            WHERE board_id = ?
            ORDER BY position, id
            """,
            (board_id,),
        ).fetchall()

    cards_by_column: dict[int, list[str]] = {int(row["id"]): [] for row in column_rows}
    cards: dict[str, dict[str, str]] = {}

    for row in card_rows:
        card_id = f"card-{int(row['id'])}"
        cards_by_column[int(row["column_id"])].append(card_id)
        cards[card_id] = {
            "id": card_id,
            "title": str(row["title"]),
            "details": str(row["details"]),
        }

    columns = [
        {
            "id": f"col-{int(row['id'])}",
            "title": str(row["title"]),
            "cardIds": cards_by_column[int(row["id"])],
        }
        for row in column_rows
    ]

    return {"columns": columns, "cards": cards}


def _reindex_column(connection: sqlite3.Connection, column_id: int) -> None:
    rows = connection.execute(
        """
        SELECT id
        FROM cards
        WHERE column_id = ?
        ORDER BY position, id
        """,
        (column_id,),
    ).fetchall()
    for index, row in enumerate(rows):
        connection.execute(
            "UPDATE cards SET position = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (index, int(row["id"])),
        )


def _rename_column(
    connection: sqlite3.Connection, board_id: int, column_id: int, title: str
) -> None:
    result = connection.execute(
        """
        UPDATE board_columns
        SET title = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND board_id = ?
        """,
        (title, column_id, board_id),
    )
    if result.rowcount == 0:
        raise ValueError("Column not found")


def _add_card(
    connection: sqlite3.Connection,
    board_id: int,
    column_id: int,
    title: str,
    details: str,
) -> int:
    column_row = connection.execute(
        "SELECT id FROM board_columns WHERE id = ? AND board_id = ?",
        (column_id, board_id),
    ).fetchone()
    if not column_row:
        raise ValueError("Column not found")

    next_position = connection.execute(
        "SELECT COUNT(*) AS count FROM cards WHERE column_id = ?",
        (column_id,),
    ).fetchone()["count"]
    cursor = connection.execute(
        """
        INSERT INTO cards (board_id, column_id, title, details, position)
        VALUES (?, ?, ?, ?, ?)
        """,
        (board_id, column_id, title, details or "", int(next_position)),
    )
    return int(cursor.lastrowid)


def _delete_card(connection: sqlite3.Connection, board_id: int, card_id: int) -> None:
    row = connection.execute(
        "SELECT id, column_id FROM cards WHERE id = ? AND board_id = ?",
        (card_id, board_id),
    ).fetchone()
    if not row:
        raise ValueError("Card not found")

    connection.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    _reindex_column(connection, int(row["column_id"]))


def _move_card(
    connection: sqlite3.Connection,
    board_id: int,
    card_id: int,
    target_column_id: int,
    over_card_id: int | None,
) -> None:
    card_row = connection.execute(
        "SELECT id, column_id, title, details FROM cards WHERE id = ? AND board_id = ?",
        (card_id, board_id),
    ).fetchone()
    if not card_row:
        raise ValueError("Card not found")

    target_row = connection.execute(
        "SELECT id FROM board_columns WHERE id = ? AND board_id = ?",
        (target_column_id, board_id),
    ).fetchone()
    if not target_row:
        raise ValueError("Target column not found")

    source_column_id = int(card_row["column_id"])
    card_title = str(card_row["title"])
    card_details = str(card_row["details"])
    connection.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    _reindex_column(connection, source_column_id)

    if over_card_id is None:
        insert_position = connection.execute(
            "SELECT COUNT(*) AS count FROM cards WHERE column_id = ?",
            (target_column_id,),
        ).fetchone()["count"]
    else:
        over_row = connection.execute(
            """
            SELECT id, position, column_id
            FROM cards
            WHERE id = ? AND board_id = ?
            """,
            (over_card_id, board_id),
        ).fetchone()
        if not over_row:
            raise ValueError("Over card not found")
        if int(over_row["column_id"]) != target_column_id:
            raise ValueError("Over card is not in target column")
        insert_position = int(over_row["position"])

    connection.execute(
        "UPDATE cards SET position = position + 1 WHERE column_id = ? AND position >= ?",
        (target_column_id, int(insert_position)),
    )
    connection.execute(
        """
        INSERT INTO cards (id, board_id, column_id, title, details, position)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            card_id,
            board_id,
            target_column_id,
            card_title,
            card_details,
            int(insert_position),
        ),
    )
    _reindex_column(connection, target_column_id)


def rename_column(username: str, column_id: int, title: str) -> None:
    board_id = ensure_user_board(username)
    with connect_db() as connection:
        _rename_column(connection, board_id, column_id, title)
        connection.commit()


def add_card(username: str, column_id: int, title: str, details: str) -> str:
    board_id = ensure_user_board(username)
    with connect_db() as connection:
        card_id = _add_card(connection, board_id, column_id, title, details)
        connection.commit()
        return f"card-{card_id}"


def delete_card(username: str, card_id: int) -> None:
    board_id = ensure_user_board(username)
    with connect_db() as connection:
        _delete_card(connection, board_id, card_id)
        connection.commit()


def move_card(
    username: str,
    card_id: int,
    target_column_id: int,
    over_card_id: int | None = None,
) -> None:
    board_id = ensure_user_board(username)
    with connect_db() as connection:
        _move_card(connection, board_id, card_id, target_column_id, over_card_id)
        connection.commit()


def parse_prefixed_id(prefix: str, value: str) -> int:
    expected = f"{prefix}-"
    if not value.startswith(expected):
        raise ValueError(f"Invalid {prefix} id")
    numeric = value[len(expected) :]
    if not numeric.isdigit():
        raise ValueError(f"Invalid {prefix} id")
    return int(numeric)


def apply_board_update_operations(username: str, operations: list[dict]) -> None:
    if not operations:
        return

    initialize_database()
    with connect_db() as connection:
        board_id = _ensure_user_board(connection, username)
        for operation in operations:
            action = operation.get("action")
            if action == "rename_column":
                column_id = parse_prefixed_id("col", str(operation["column_id"]))
                title = str(operation.get("title", "")).strip()
                if not title:
                    raise ValueError("rename_column requires non-empty title")
                _rename_column(connection, board_id, column_id, title)
            elif action == "add_card":
                column_id = parse_prefixed_id("col", str(operation["column_id"]))
                title = str(operation.get("title", "")).strip()
                details = str(operation.get("details", "")).strip()
                if not title:
                    raise ValueError("add_card requires non-empty title")
                _add_card(connection, board_id, column_id, title, details)
            elif action == "delete_card":
                card_id = parse_prefixed_id("card", str(operation["card_id"]))
                _delete_card(connection, board_id, card_id)
            elif action == "move_card":
                card_id = parse_prefixed_id("card", str(operation["card_id"]))
                target_column_id = parse_prefixed_id(
                    "col", str(operation["target_column_id"])
                )
                over_card_value = operation.get("over_card_id")
                over_card_id = (
                    parse_prefixed_id("card", str(over_card_value))
                    if over_card_value
                    else None
                )
                _move_card(
                    connection, board_id, card_id, target_column_id, over_card_id
                )
            else:
                raise ValueError(f"Unsupported board action: {action}")
        connection.commit()
