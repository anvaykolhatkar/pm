from pathlib import Path
from secrets import token_urlsafe

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.ai import run_ai_chat_prompt, run_ai_ping
from app.ai_structured import (
    ChatHistoryMessage,
    build_structured_chat_prompt,
    parse_structured_ai_response,
)
from app.db import (
    add_card,
    apply_board_update_operations,
    delete_card,
    get_board_data,
    initialize_database,
    move_card,
    parse_prefixed_id as db_parse_prefixed_id,
    rename_column,
)

app = FastAPI(title="PM MVP Backend")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"
SESSION_COOKIE = "pm_session"
VALID_USERNAME = "user"
VALID_PASSWORD = "password"
SESSIONS: dict[str, str] = {}


class LoginPayload(BaseModel):
    username: str
    password: str


class RenameColumnPayload(BaseModel):
    title: str


class AddCardPayload(BaseModel):
    title: str
    details: str = ""


class MoveCardPayload(BaseModel):
    target_column_id: str
    over_card_id: str | None = None


class AiPingPayload(BaseModel):
    prompt: str = "What is 2+2? Return only the numeric answer."


class AiChatPayload(BaseModel):
    question: str
    history: list[ChatHistoryMessage] = Field(default_factory=list)


def parse_prefixed_id(prefix: str, value: str) -> int:
    try:
        return db_parse_prefixed_id(prefix, value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def get_authenticated_username(request: Request) -> str | None:
    session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        return None
    return SESSIONS.get(session_token)


def is_authenticated(request: Request) -> bool:
    return get_authenticated_username(request) is not None


def require_auth_or_redirect(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return None


def require_api_user(request: Request) -> str:
    username = get_authenticated_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")
    return username


@app.get("/login", response_class=HTMLResponse)
def read_login_page() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Sign in - PM MVP</title>
    <style>
      body {
        margin: 0;
        font-family: Arial, sans-serif;
        background: #f7f8fb;
        color: #032147;
      }
      .wrap {
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 1.5rem;
      }
      .card {
        width: 100%;
        max-width: 420px;
        background: #fff;
        border: 1px solid rgba(3, 33, 71, 0.12);
        border-radius: 14px;
        padding: 1.25rem;
        box-shadow: 0 12px 30px rgba(3, 33, 71, 0.1);
      }
      h1 {
        margin: 0 0 0.35rem 0;
      }
      p {
        margin: 0.25rem 0 1rem 0;
        color: #888888;
      }
      label {
        display: block;
        margin-bottom: 0.4rem;
        font-weight: 600;
      }
      input {
        width: 100%;
        border: 1px solid rgba(3, 33, 71, 0.2);
        border-radius: 8px;
        padding: 0.6rem;
        margin-bottom: 0.9rem;
      }
      button {
        width: 100%;
        border: 0;
        border-radius: 999px;
        padding: 0.65rem;
        background: #753991;
        color: white;
        font-weight: 700;
        cursor: pointer;
      }
      .error {
        margin-top: 0.8rem;
        color: #b91c1c;
        min-height: 1.2rem;
      }
      .hint {
        margin-top: 0.8rem;
        font-size: 0.85rem;
      }
    </style>
  </head>
  <body>
    <main class="wrap">
      <section class="card">
        <h1>Sign in</h1>
        <p>Use the MVP credentials to access your board.</p>
        <form id="login-form">
          <label for="username">Username</label>
          <input id="username" name="username" value="user" autocomplete="username" required />
          <label for="password">Password</label>
          <input id="password" name="password" type="password" value="password" autocomplete="current-password" required />
          <button type="submit">Sign in</button>
        </form>
        <div id="error" class="error"></div>
        <div class="hint">MVP credentials: user / password</div>
      </section>
    </main>
    <script>
      const form = document.getElementById("login-form");
      const error = document.getElementById("error");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        error.textContent = "";
        const payload = {
          username: form.username.value,
          password: form.password.value
        };
        const res = await fetch("/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          window.location.href = "/";
          return;
        }
        error.textContent = "Invalid username or password.";
      });
    </script>
  </body>
</html>
""",
        status_code=200,
    )


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    redirect = require_auth_or_redirect(request)
    if redirect:
        return redirect

    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return HTMLResponse("<h1>Hello from FastAPI</h1>", status_code=200)


@app.get("/api/health")
def read_health() -> dict[str, str]:
    return {"status": "ok", "service": "pm-backend"}


@app.post("/api/login")
def login(payload: LoginPayload, response: Response) -> dict[str, str]:
    if payload.username != VALID_USERNAME or payload.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = token_urlsafe(24)
    SESSIONS[token] = payload.username
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"status": "ok"}


@app.post("/api/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    session_token = request.cookies.get(SESSION_COOKIE)
    if session_token and session_token in SESSIONS:
        del SESSIONS[session_token]
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"status": "ok"}


@app.get("/api/board")
def read_board(request: Request) -> dict:
    username = require_api_user(request)
    return get_board_data(username)


@app.patch("/api/columns/{column_id}")
def update_column_title(
    column_id: str, payload: RenameColumnPayload, request: Request
) -> dict[str, str]:
    username = require_api_user(request)
    numeric_column_id = parse_prefixed_id("col", column_id)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    try:
        rename_column(username, numeric_column_id, title)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok"}


@app.post("/api/columns/{column_id}/cards")
def create_card(column_id: str, payload: AddCardPayload, request: Request) -> dict[str, str]:
    username = require_api_user(request)
    numeric_column_id = parse_prefixed_id("col", column_id)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    try:
        new_id = add_card(username, numeric_column_id, title, payload.details.strip())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "card_id": new_id}


@app.delete("/api/cards/{card_id}")
def remove_card(card_id: str, request: Request) -> dict[str, str]:
    username = require_api_user(request)
    numeric_card_id = parse_prefixed_id("card", card_id)
    try:
        delete_card(username, numeric_card_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok"}


@app.post("/api/cards/{card_id}/move")
def move_card_to_column(
    card_id: str, payload: MoveCardPayload, request: Request
) -> dict[str, str]:
    username = require_api_user(request)
    numeric_card_id = parse_prefixed_id("card", card_id)
    numeric_target_column_id = parse_prefixed_id("col", payload.target_column_id)
    numeric_over_card_id = (
        parse_prefixed_id("card", payload.over_card_id) if payload.over_card_id else None
    )
    try:
        move_card(
            username,
            numeric_card_id,
            numeric_target_column_id,
            numeric_over_card_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok"}


@app.post("/api/ai/ping")
def ai_ping(payload: AiPingPayload, request: Request) -> dict[str, str]:
    require_api_user(request)
    try:
        response_text = run_ai_ping(payload.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}") from exc
    return {"status": "ok", "model": "claude-haiku-4-5-20251001", "response": response_text}


@app.post("/api/ai/chat")
def ai_chat(payload: AiChatPayload, request: Request) -> dict:
    username = require_api_user(request)
    board_data = get_board_data(username)
    prompt = build_structured_chat_prompt(board_data, payload.question, payload.history)

    try:
        raw_response = run_ai_chat_prompt(prompt)
        structured = parse_structured_ai_response(raw_response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}") from exc

    if structured.board_update:
        try:
            apply_board_update_operations(
                username,
                [operation.model_dump(exclude_none=True) for operation in structured.board_update],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid board update: {exc}") from exc

    updated_board = get_board_data(username)
    return {
        "status": "ok",
        "model": "claude-haiku-4-5-20251001",
        "response": structured.response,
        "board_updated": bool(structured.board_update),
        "board": updated_board,
    }


@app.get("/{full_path:path}")
def read_static_file(full_path: str, request: Request):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    redirect = require_auth_or_redirect(request)
    if redirect:
        return redirect

    target_path = STATIC_DIR / full_path

    if target_path.is_dir():
        nested_index = target_path / "index.html"
        if nested_index.exists():
            return FileResponse(nested_index)

    if target_path.exists() and target_path.is_file():
        return FileResponse(target_path)

    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)

    raise HTTPException(status_code=404, detail="Static file not found")


initialize_database()
