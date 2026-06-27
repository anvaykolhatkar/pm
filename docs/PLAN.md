# Project Plan

## Confirmed decisions

- AI provider: Anthropic direct API (no OpenRouter).
- AI model (pinned): `claude-haiku-4-5-20251001`.
- Database shape: normalized relational schema with optional JSON fields where useful.
- Auth for MVP: server validates `user` / `password`.
- Test strategy: minimum viable tests per phase (targeted, not exhaustive).
- App serving model: FastAPI serves the app at `/`.

## Part 1: Planning and baseline documentation

### Checklist

- [x] Finalize this plan with per-phase scope, tests, and success criteria.
- [x] Add `frontend/AGENTS.md` describing the current frontend-only demo structure and assumptions.
- [x] Get user sign-off on plan and sequencing before implementation.

### Minimum tests

- [ ] No code tests required in this phase.
- [ ] Validate docs for consistency with root `AGENTS.md`.

### Success criteria

- [ ] Plan is explicit enough to execute phase-by-phase without ambiguity.
- [ ] User has approved the written plan.

## Part 2: Scaffolding (Docker + FastAPI + scripts)

### Checklist

- [x] Create backend scaffold in `backend/` with FastAPI app entrypoint.
- [x] Add Dockerfile and any required compose/runtime config for local containerized execution.
- [x] Add start/stop scripts for Mac, Linux, and Windows in `scripts/`.
- [ ] Implement baseline FastAPI routes:
  - [x] `GET /` serves static hello-world HTML.
  - [x] `GET /api/health` (or equivalent) returns simple JSON.

### Minimum tests

- [x] Backend smoke test: app starts and serves `GET /` and one API route.
- [x] Script smoke checks: each platform script has basic start/stop path verified.

### Success criteria

- [x] `docker` run starts app locally without manual patching.
- [x] Browser can load `/` and receive hello-world page from FastAPI.
- [x] API health route returns success JSON.

## Part 3: Integrate existing frontend build output

### Checklist

- [x] Configure frontend build for static output compatible with FastAPI static serving.
- [x] Build frontend demo Kanban and serve at `/` via FastAPI.
- [x] Ensure static assets resolve correctly under container runtime.

### Minimum tests

- [x] Frontend build command succeeds in clean environment.
- [x] One integration smoke test: `GET /` returns Kanban page content.

### Success criteria

- [x] The existing demo Kanban appears at `/` when app is run via backend container path.

## Part 4: Fake sign-in flow (server-validated)

### Checklist

- [x] Add login endpoint that validates fixed credentials (`user` / `password`) on server.
- [x] Add simple session mechanism (cookie-based) to protect Kanban page/API.
- [x] Add logout endpoint and frontend logout action.
- [x] Redirect unauthenticated users to login screen before Kanban.

### Minimum tests

- [x] Auth unit test: valid credentials accepted, invalid rejected.
- [x] Auth integration test: protected route blocked without session.
- [x] Logout test: session invalidated.

### Success criteria

- [x] User cannot reach Kanban unless logged in.
- [x] Login with `user` / `password` succeeds and persists for session.
- [x] Logout returns user to unauthenticated state.

## Part 5: Database modeling and documentation

### Checklist

- [x] Propose and document normalized SQLite schema (users, boards, columns, cards, optional chat tables if needed).
- [x] Include optional JSON fields only where flexibility is needed (for metadata).
- [x] Define migration/initialization strategy (create DB if missing).
- [ ] Get user sign-off before implementing full data flow.

### Minimum tests

- [x] Schema creation smoke test: DB file and tables created from empty state.
- [x] Basic relational integrity test (foreign keys).

### Success criteria

- [x] Database design is documented in `docs/`.
- [x] Schema supports one board per user now and multiple users later.

## Part 6: Backend Kanban APIs

### Checklist

- [x] Add backend routes to fetch/update Kanban state for authenticated user.
- [x] Implement create/update/move card operations and column rename operations.
- [x] Map operations to normalized schema with transactional safety.
- [x] Ensure DB auto-creates if absent.

### Minimum tests

- [x] Unit tests for service functions handling card/column operations.
- [x] Integration tests for core endpoints and auth checks.

### Success criteria

- [x] API supports all Kanban operations required by UI.
- [x] Data persists across restarts.

## Part 7: Connect frontend to backend persistence

### Checklist

- [x] Replace local/demo state with backend API-backed state.
- [x] Wire CRUD and drag/drop updates to backend calls.
- [x] Handle basic loading/error states without overengineering.

### Minimum tests

- [x] Frontend integration test for initial board load.
- [x] Frontend integration test for one card move + persistence check.

### Success criteria

- [x] Kanban operations persist through page refresh and app restart.

## Part 8: AI connectivity (Anthropic direct)

### Checklist

- [x] Add backend AI client using `ANTHROPIC_API_KEY`.
- [x] Use pinned model ID `claude-haiku-4-5-20251001`.
- [x] Add simple connectivity route/service invocation.
- [x] Verify with a deterministic smoke prompt (for example, "2+2").

### Minimum tests

- [x] Unit test with mocked Anthropic client.
- [x] Manual connectivity smoke test in local environment.

### Success criteria

- [x] Backend can successfully call Anthropic with configured key and model.

## Part 9: AI + board context + structured response contract

### Checklist

- [x] Send Kanban JSON context + user prompt + conversation history to backend AI service.
- [ ] Define strict structured response format:
  - [x] assistant text response
  - [x] optional board update payload
- [x] Validate and parse AI output before applying updates.
- [x] Apply valid updates transactionally and return updated board state.

### Minimum tests

- [x] Parser/validator unit tests (valid + malformed responses).
- [x] Integration test for "chat only" response.
- [x] Integration test for "chat + board update" response.

### Success criteria

- [x] AI can reply conversationally and optionally mutate board state safely.

## Part 10: Sidebar AI chat UX

### Checklist

- [x] Add sidebar chat UI to Kanban screen.
- [x] Render conversation history and pending/loading states.
- [x] Call backend chat endpoint and display response.
- [x] If AI update payload is returned, refresh/merge Kanban state automatically.
- [x] Keep styling aligned with project color scheme.

### Minimum tests

- [x] Frontend integration test for sending chat and rendering AI reply.
- [x] Frontend integration test for AI-triggered board update refresh.

### Success criteria

- [x] User can chat with AI in sidebar and see board update automatically when AI returns changes.