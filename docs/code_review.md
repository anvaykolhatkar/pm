# Code Review

Reviewed against the MVP scope in AGENTS.md. Organised by severity: bugs first, then code quality, then minor/UX, then test quality.

---

## Bugs

### 1. SQLite database is not persisted across Docker container restarts

`docker-compose.yml` exposes port 8000 and reads `.env`, but mounts no volume. The database lives at `backend/data/pm.db` inside the container image layer. Every `docker compose up --build` destroys all board data.

**Fix:** add a named volume for the data directory.

```yaml
services:
  app:
    ...
    volumes:
      - pm-data:/app/backend/data

volumes:
  pm-data:
```

### 2. `parse_prefixed_id` is duplicated

`main.py` defines `parse_prefixed_id` (lines 63-70). `db.py` defines `_parse_prefixed_id` (lines 388-395). They are identical. Both are called from their respective modules.

**Fix:** delete one and import the other. The function belongs in `db.py` since it is the module that works with IDs; `main.py` should import and call it.

---

## Code quality

### 3. `move_card` logic copy-pasted into `apply_board_update_operations`

The `move_card` branch inside `apply_board_update_operations` (db.py lines 454-524) is a near-verbatim copy of the standalone `move_card` function (db.py lines 318-385). Same for the delete-and-reindex pattern for `delete_card`. The duplication is ~70 lines.

The reason this exists is that `apply_board_update_operations` needs to run all operations in a single SQLite transaction. The individual functions each open their own connection, so they cannot be composed.

**Fix:** extract internal helpers that accept a `connection` parameter — `_move_card(conn, board_id, ...)`, `_add_card(conn, board_id, ...)`, etc. The public functions call `ensure_user_board` then delegate to the helpers. `apply_board_update_operations` does the same but shares one connection across all operations.

### 4. Anthropic client is instantiated on every API call

In `ai.py`, both `run_ai_ping` and `run_ai_chat_prompt` construct `Anthropic(api_key=api_key)` on every invocation and also call `os.getenv` on every call. The client is safe to share across requests.

**Fix:** instantiate once at module level (after validating the key at startup), or use a cached property.

```python
_client: Anthropic | None = None

def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        _client = Anthropic(api_key=api_key)
    return _client
```

### 5. `ensure_user_board` is called redundantly in batch operations

`apply_board_update_operations` calls `ensure_user_board(username)` at the top, which opens its own connection to seed the board if needed. It then opens a second connection for the operations. Each individual function (`rename_column`, `add_card`, etc.) also calls `ensure_user_board` at their top, which opens yet more connections. This is harmless for SQLite writes in this access pattern but is wasteful and confusing. Resolved by fix #3 above.

### 6. AI `max_tokens` is 900 — may truncate complex responses

`run_ai_chat_prompt` in `ai.py` sets `max_tokens=900`. The structured response must contain a `response` string plus an optional JSON array of board operations. A moderately verbose reply with several operations can approach this limit; a truncated JSON response will fail parsing and return a 400 to the user.

**Fix:** raise to at least 2048. There is no correctness reason to keep it at 900.

### 7. Chat history sent to Anthropic as embedded JSON, not as API messages

`build_structured_chat_prompt` serialises the conversation history into the text of a single user message. The Anthropic API supports alternating `user`/`assistant` turns natively, which gives the model better context and is more token-efficient.

This is not a bug — the current approach works — but it means history context degrades over long conversations and the entire prompt grows with every turn. For MVP, acceptable.

---

## Minor / UX

### 8. No optimistic update on drag-and-drop move

`handleDragEnd` in `KanbanBoard.tsx` awaits `moveCard(...)` then `loadBoard()` before updating state. During the round-trip the card snaps back to its original column visually, then jumps to the target column after the re-fetch. A user doing rapid moves will see jarring reflows.

**Fix for post-MVP:** apply the move locally with `moveCard()` from `kanban.ts`, then fire the API call in the background and revert only on error.

### 9. No request guard against concurrent drag operations

If the user drags a second card before the first move API call returns, two `moveCard` + `loadBoard` chains run in parallel. The second `loadBoard` may complete before the first, producing a stale board state.

**Fix:** disable the `DndContext` (or set a loading flag) while a move is in flight.

### 10. Chat input is cleared before knowing if the API call will succeed

In `handleSendChat`, `setChatInput("")` is called before `await chatWithAi(...)`. If the call fails, the user's typed question is lost and they must retype it.

**Fix:** clear the input only on success.

### 11. Logout has no error handling

`handleLogout` fires `fetch("/api/logout", ...)` without awaiting or checking the result, then unconditionally redirects to `/login`. If the session were a real token (e.g., JWT), a failed logout would leave a live token. For the in-memory MVP session this is harmless, but the pattern is worth correcting.

---

## Test quality

### 12. `sys.path.append` in every test file

All seven test files open with:

```python
sys.path.append(str(Path(__file__).resolve().parents[1]))
```

This is fragile (the `parents[1]` assumption breaks if files are moved) and pollutes `sys.path`. The cleaner fix is to add a `[tool.pytest.ini_options]` `pythonpath` entry to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

Then all imports work without manual path manipulation.

### 13. Module-level `TestClient` is shared across tests with incomplete isolation

In `test_kanban_api.py`, `test_smoke.py`, and `test_ai_chat_api.py`, `client = TestClient(app)` is created once at module level. Tests that call `setup_db()` clear both `SESSIONS` and `client.cookies`. Tests that do not call `setup_db()` — such as `test_board_requires_auth` and `test_root_requires_auth` — clear `SESSIONS` but not `client.cookies`. A cookie from a prior test pointing to a now-cleared session won't authenticate (because `SESSIONS.get(token)` returns `None`), so these tests currently pass by accident. If session logic changes, isolation breaks.

**Fix:** move `SESSIONS.clear(); client.cookies.clear()` into a `setup_function` or autouse fixture, or create the `TestClient` fresh per-test.

### 14. AI board-update test hardcodes `col-1`

`test_ai_chat_with_board_update` patches the AI to return `column_id: "col-1"` and then asserts `body["board"]["columns"][0]["title"] == "Ideas"`. This relies on the seeded DB always assigning SQLite id 1 to the first column. It holds today but would silently break if seeding order or the DB path changes.

**Fix:** fetch `/api/board` first, extract the actual first column id, and use that in the patched response.

### 15. Frontend static build must be manually copied for non-Docker testing

`backend/static/` ships a placeholder `index.html`. For e2e tests to hit the real frontend, the Next.js app must be built (`npm run build` in `frontend/`) and the `out/` directory copied to `backend/static/`. This step is automatic inside Docker but is invisible to anyone running tests locally without reading the Dockerfile. The e2e test suite fails silently on a heading-not-found error rather than a clear "static build missing" message.

**Fix (short term):** document the step in CLAUDE.md under "Frontend E2E tests". Done in the CLAUDE.md created at the start of this session.

**Fix (better):** add a `Makefile` target or a small script that does `cd frontend && npm run build && cp -r out/ ../backend/static/`, and invoke it in CI before running e2e.

---

## Summary table

| # | Area | Severity | Action |
|---|------|----------|--------|
| 1 | Docker volume missing | Bug — data loss | Add volume to `docker-compose.yml` |
| 2 | Duplicated `parse_prefixed_id` | Bug-risk / quality | Delete one, import the other |
| 3 | `move_card` logic copy-pasted | Quality | Extract connection-level helpers |
| 4 | Anthropic client per request | Quality | Instantiate once at module level |
| 5 | Redundant `ensure_user_board` calls | Quality | Resolved by fix #3 |
| 6 | `max_tokens=900` too low | Bug-risk | Raise to 2048 |
| 7 | History as embedded JSON | Quality | Acceptable for MVP |
| 8 | No optimistic update on drag | UX | Post-MVP |
| 9 | No drag concurrency guard | UX | Post-MVP |
| 10 | Chat input cleared on failure | UX | Clear only on success |
| 11 | Logout ignores errors | Quality | Add `await` and error check |
| 12 | `sys.path.append` in tests | Quality | Use `pythonpath` in `pyproject.toml` |
| 13 | Shared `TestClient`, incomplete isolation | Test quality | Autouse fixture |
| 14 | Hardcoded `col-1` in AI test | Test quality | Fetch real id first |
| 15 | E2E needs manual static copy | Workflow | Document; add build script |
