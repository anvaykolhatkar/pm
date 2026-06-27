# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Project Management MVP: a Kanban board web app with an AI chat sidebar. FastAPI (Python) serves the Next.js static build and all API routes. Runs in a single Docker container.

## Commands

### Run the app (Docker)

```powershell
# Windows
.\scripts\start-windows.ps1
.\scripts\stop-windows.ps1
```

```bash
# Mac / Linux
./scripts/start-mac.sh
./scripts/stop-mac.sh
```

App runs at `http://localhost:8000`. Login with `user` / `password`.

### Backend (Python / uv)

Run from `backend/`:

```bash
uv run pytest                        # all backend tests
uv run pytest tests/test_smoke.py    # single test file
uv run uvicorn app.main:app --reload # dev server (port 8000)
```

### Frontend (Next.js / npm)

Run from `frontend/`:

```bash
npm install
npm run dev          # dev server (port 3000, standalone frontend only)
npm run build        # static export → out/
npm run test:unit    # vitest unit tests
npm run test:e2e     # playwright e2e (requires app running at :8000)
npm run lint         # eslint
```

Run a single vitest test file:

```bash
npm run test:unit -- src/components/KanbanBoard.test.tsx
```

## Architecture

```
Dockerfile
  └─ stage 1: builds Next.js → out/
  └─ stage 2: Python 3.12 + uv, copies out/ → backend/static/

docker-compose.yml   → single service "pm-app" on port 8000, reads .env

backend/
  app/
    main.py          → FastAPI app, all routes, session auth (in-memory SESSIONS dict)
    db.py            → SQLite init + all DB operations (get_board_data, add_card, move_card, …)
    ai.py            → Anthropic client wrapper (run_ai_ping, run_ai_chat_prompt)
    ai_structured.py → structured response model, prompt builder, parser
  static/            → built Next.js output served by FastAPI at /
  data/pm.db         → SQLite file (auto-created; override with PM_DB_PATH env var)
  tests/             → pytest suite

frontend/
  src/
    app/page.tsx           → root page
    components/
      KanbanBoard.tsx      → board-level state, DnD orchestration, AI sidebar
      KanbanColumn.tsx     → column UI, rename, card list, add-card form
      KanbanCard.tsx       → sortable card item
      NewCardForm.tsx      → add-card form
    lib/
      kanban.ts            → Board/Column/Card types, moveCard logic
      api.ts               → all fetch calls to the backend API
    app/globals.css        → design tokens / global styles
  tests/kanban.spec.ts     → Playwright e2e tests
```

### Request flow

1. Browser hits `http://localhost:8000` → FastAPI checks session cookie.
2. Unauthenticated: redirect to `/login` (inline HTML served by FastAPI).
3. Authenticated: `FileResponse(backend/static/index.html)` — the Next.js SPA.
4. SPA calls `/api/*` endpoints; FastAPI enforces auth on every API route via `require_api_user`.
5. AI chat: `POST /api/ai/chat` sends board JSON + history to Anthropic, parses structured response, applies any board mutations transactionally, returns updated board.

### ID format

Cards and columns use prefixed string IDs in the API (`card-{n}`, `col-{n}`). `parse_prefixed_id` in `main.py` strips the prefix to get the SQLite integer PK.

### AI model

Pinned to `claude-haiku-4-5-20251001` (fast, cheap). Do not change without updating both `ai.py` and `ai_structured.py`.

## Key constraints

- MVP auth is hardcoded (`user` / `password`). Sessions live in an in-memory dict — restarts log everyone out.
- One board per user. Schema supports multiple users and boards but the API assumes one board per user.
- SQLite DB auto-initializes on startup (`initialize_database()` called at module level in `main.py`).
- Frontend E2E tests hit the live app at `:8000`, so the backend must be running first.
- `ANTHROPIC_API_KEY` must be in a `.env` file at the project root for AI features to work.

## Style rules (from AGENTS.md)

- No over-engineering, no unnecessary defensive programming, no extra features.
- No emojis anywhere.
- Identify root cause before attempting a fix; prove with evidence.
- Keep READMEs and docs minimal.
