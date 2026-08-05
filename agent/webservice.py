import json
import os
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from agent.session import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "agent" / "config.yml"

with CONFIG_PATH.open("r", encoding="utf-8") as file_obj:
    config = yaml.safe_load(file_obj)

SESSION_DIR = (PROJECT_ROOT / config["session"]).resolve()
WORKSPACE_DIR = (PROJECT_ROOT / config["workspace"]).resolve()
MEMORY_DIR = (PROJECT_ROOT / config["memory"]).resolve()

SESSION_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Agent Browser Control")
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "agent" / "static")), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "agent" / "templates"))

ACTIVE_RUNS: dict[str, dict[str, Any]] = {}


def _session_listing() -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []

    for session_file in sorted(SESSION_DIR.glob("session_*.sqlite3")):
        session_id = session_file.stem.replace("session_", "")
        try:
            with sqlite3.connect(session_file) as connection:
                connection.row_factory = sqlite3.Row
                session_row = connection.execute(
                    "SELECT created_at, summary FROM sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
                message_count = connection.execute(
                    "SELECT COUNT(*) AS count FROM messages WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                message_rows = connection.execute(
                    "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
        except sqlite3.Error:
            continue

        sessions.append(
            {
                "id": session_id,
                "created_at": session_row["created_at"] if session_row else None,
                "summary": session_row["summary"] if session_row else None,
                "message_count": message_count["count"] if message_count else 0,
                "latest_role": message_rows["role"] if message_rows else None,
                "latest_content": message_rows["content"] if message_rows else None,
            }
        )

    sessions.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return sessions


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    sessions = _session_listing()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "sessions": sessions,
            "active_runs": ACTIVE_RUNS,
        },
    )


@app.post("/sessions/run")
async def run_session(prompt: str = Form(...)):
    command = [
        "agentv5",
        "--workspace",
        "agent_workspace",
        "--test",
        "false",
        "--interactive",
        "false",
        "--initial_prompt",
        prompt,
    ]

    process = subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    ACTIVE_RUNS[str(process.pid)] = {
        "pid": process.pid,
        "prompt": prompt,
        "status": "running",
    }

    return RedirectResponse(url="/", status_code=303)


@app.get("/sessions/{session_id}", response_class=HTMLResponse)
async def session_detail(request: Request, session_id: str):
    session = Session(
        session_folder=str(SESSION_DIR),
        workspace_folder=str(WORKSPACE_DIR),
        memory_folder=str(MEMORY_DIR),
        id=session_id,
    )

    messages = session.get_messages_for_agent(max_recent_messages=None)
    return templates.TemplateResponse(
        request=request,
        name="session.html",
        context={
            "session_id": session_id,
            "messages": messages,
        },
    )


@app.get("/api/sessions")
async def api_sessions():
    return {"sessions": _session_listing()}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


def main():
    import uvicorn

    uvicorn.run("agent.webservice:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
