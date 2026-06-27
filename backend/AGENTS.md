## Backend overview

`backend/` contains the FastAPI service for the Project Management MVP.

Current scope in this phase:

- App entrypoint in `backend/app/main.py`
- `GET /` serves static hello-world HTML from `backend/static/index.html`
- `GET /api/health` serves a JSON health payload
- Smoke tests in `backend/tests/test_smoke.py`
- Dependency and tooling setup in `backend/pyproject.toml` (managed with `uv`)
- SQLite schema initializer in `backend/app/db.py`
- DB schema tests in `backend/tests/test_db_schema.py`
- Kanban API routes in `backend/app/main.py` (`/api/board`, column rename, card add/delete/move)
- Kanban API integration tests in `backend/tests/test_kanban_api.py`
- Kanban DB operation tests in `backend/tests/test_db_operations.py`
- Anthropic connectivity service in `backend/app/ai.py` using pinned model `claude-haiku-4-5-20251001`
- AI connectivity endpoint in `backend/app/main.py` at `/api/ai/ping`
- AI endpoint tests in `backend/tests/test_ai_ping.py`
- Structured AI response models/parser in `backend/app/ai_structured.py`
- AI chat endpoint in `backend/app/main.py` at `/api/ai/chat` with optional transactional board updates
- AI chat tests in `backend/tests/test_ai_structured.py` and `backend/tests/test_ai_chat_api.py`

Upcoming phases will extend this service with:

- Auth endpoints and session checks
- SQLite schema and persistence
- Kanban CRUD APIs
- Anthropic AI integration