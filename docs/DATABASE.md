# Database Design (Part 5)

## Goals

- Use SQLite for local MVP persistence.
- Use a normalized relational schema for core Kanban entities.
- Keep one board per user for MVP, while allowing multiple users in schema.
- Allow limited flexibility with optional JSON metadata fields.

## SQLite file location

- Default path: `backend/data/pm.db`
- Override path: `PM_DB_PATH` environment variable

## Schema overview

### `schema_migrations`

Tracks current schema version for simple in-app migrations.

- `version` INTEGER PRIMARY KEY
- `applied_at` TEXT NOT NULL (UTC timestamp)

### `users`

Represents users now and in future multi-user support.

- `id` INTEGER PRIMARY KEY
- `username` TEXT NOT NULL UNIQUE
- `created_at` TEXT NOT NULL
- `metadata_json` TEXT NULL

Notes:
- MVP auth remains fixed `user`/`password` at API level for now.
- This table prepares migration to DB-backed auth later.

### `boards`

One board per user in MVP, enforced by unique constraint.

- `id` INTEGER PRIMARY KEY
- `user_id` INTEGER NOT NULL REFERENCES `users(id)` ON DELETE CASCADE
- `name` TEXT NOT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL
- `metadata_json` TEXT NULL
- `UNIQUE(user_id)`

### `board_columns`

Columns belonging to a board in explicit order.

- `id` INTEGER PRIMARY KEY
- `board_id` INTEGER NOT NULL REFERENCES `boards(id)` ON DELETE CASCADE
- `title` TEXT NOT NULL
- `position` INTEGER NOT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL
- `metadata_json` TEXT NULL
- `UNIQUE(board_id, position)`

### `cards`

Cards belonging to a board and current column, with ordered position.

- `id` INTEGER PRIMARY KEY
- `board_id` INTEGER NOT NULL REFERENCES `boards(id)` ON DELETE CASCADE
- `column_id` INTEGER NOT NULL REFERENCES `board_columns(id)` ON DELETE CASCADE
- `title` TEXT NOT NULL
- `details` TEXT NOT NULL DEFAULT ''
- `position` INTEGER NOT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL
- `metadata_json` TEXT NULL
- `UNIQUE(column_id, position)`

## Why this is normalized

- Users, boards, columns, and cards are separate entities with explicit foreign keys.
- Ordering is represented by `position` columns instead of nested JSON arrays.
- Optional metadata is isolated to `metadata_json` and does not replace relational fields.

## Migration and initialization strategy

1. On backend startup (or first DB access), call `initialize_database()`.
2. Ensure DB directory exists.
3. Open SQLite connection with `PRAGMA foreign_keys=ON`.
4. Create core tables using `CREATE TABLE IF NOT EXISTS`.
5. Insert/update migration row in `schema_migrations` with current schema version.

For MVP, migrations are simple and monotonic:

- Current schema version: `1`
- Future schema changes should add a new version step rather than destructive rewrites.

## Notes for next phase (Part 6)

- Seed/ensure a user record for `user` when needed.
- Seed one default board with five columns on first load.
- Use transactions for operations that move cards across columns.
