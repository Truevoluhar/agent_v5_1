"""Independent dashboard for browsing/manipulating the shared bind-mounted data.

This mirrors the former agent/webservice.py, but has no dependency on the
agent package - it only reads the sqlite session databases and the shared
filesystem directly. Gives full control over sessions (create/read/edit/
delete sessions and messages) and files (browse/read/write/upload/mkdir/
move/delete) under session/, memory/, agent_workspace/, resources/.
"""
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from client import fsops
from client import sessions as sessions_ops
from client.paths import MEMORY_DIR, RESOURCES_DIR, SESSION_DIR, WORKSPACE_DIR
from client.user_storage import UserStoragePaths, user_storage_paths

CLIENT_ROOT = Path(__file__).resolve().parent

SESSION_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

_ROOTS = {
    "session": SESSION_DIR,
    "memory": MEMORY_DIR,
    "workspace": WORKSPACE_DIR,
    "resources": RESOURCES_DIR,
}

app = FastAPI(title="Agent Data Client")
app.mount("/static", StaticFiles(directory=str(CLIENT_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(CLIENT_ROOT / "templates"))


def _user_storage(username: str) -> UserStoragePaths:
    try:
        return user_storage_paths(
            username,
            session_folder=SESSION_DIR,
            memory_folder=MEMORY_DIR,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _root(root_name: str) -> Path:
    if root_name not in _ROOTS:
        raise HTTPException(status_code=400, detail=f"unknown root: {root_name}")
    return _ROOTS[root_name]


# ---------------------------------------------------------------------------
# Dashboard / sessions UI
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, username: str = Query(...)):
    storage = _user_storage(username)
    sessions = sessions_ops.list_sessions(Path(storage.session_folder))
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "sessions": sessions,
            "username": username,
            "roots": list(_ROOTS),
        },
    )


@app.post("/sessions/create")
async def create_session(username: str = Form(...)):
    storage = _user_storage(username)
    session_id = sessions_ops.create_session(Path(storage.session_folder))
    return RedirectResponse(url=f"/sessions/{session_id}?username={username}", status_code=303)


@app.post("/sessions/{session_id}/delete")
async def delete_session_route(session_id: str, username: str = Form(...)):
    storage = _user_storage(username)
    sessions_ops.delete_session(Path(storage.session_folder), session_id)
    return RedirectResponse(url=f"/?username={username}", status_code=303)


@app.post("/sessions/{session_id}/summary")
async def set_summary_route(session_id: str, username: str = Form(...), summary: str = Form(...)):
    storage = _user_storage(username)
    if not sessions_ops.set_summary(Path(storage.session_folder), session_id, summary):
        raise HTTPException(status_code=404, detail="Session not found")
    return RedirectResponse(url=f"/sessions/{session_id}?username={username}", status_code=303)


@app.get("/sessions/{session_id}", response_class=HTMLResponse)
async def session_detail(request: Request, session_id: str, username: str = Query(...)):
    storage = _user_storage(username)
    session_dir = Path(storage.session_folder)
    if not (session_dir / f"session_{session_id}.sqlite3").is_file():
        raise HTTPException(status_code=404, detail="Session not found")

    messages = sessions_ops.read_session_messages(session_dir, session_id)
    return templates.TemplateResponse(
        request=request,
        name="session.html",
        context={
            "session_id": session_id,
            "messages": messages,
            "username": username,
        },
    )


@app.post("/sessions/{session_id}/messages/add")
async def add_message_route(
    session_id: str,
    username: str = Form(...),
    role: str = Form(...),
    content: str = Form(...),
):
    storage = _user_storage(username)
    sessions_ops.add_message(Path(storage.session_folder), session_id, role, content)
    return RedirectResponse(url=f"/sessions/{session_id}?username={username}", status_code=303)


@app.post("/sessions/{session_id}/messages/{message_id}/update")
async def update_message_route(
    session_id: str,
    message_id: int,
    username: str = Form(...),
    content: str = Form(...),
):
    storage = _user_storage(username)
    sessions_ops.update_message(Path(storage.session_folder), session_id, message_id, content)
    return RedirectResponse(url=f"/sessions/{session_id}?username={username}", status_code=303)


@app.post("/sessions/{session_id}/messages/{message_id}/delete")
async def delete_message_route(session_id: str, message_id: int, username: str = Form(...)):
    storage = _user_storage(username)
    sessions_ops.delete_message(Path(storage.session_folder), session_id, message_id)
    return RedirectResponse(url=f"/sessions/{session_id}?username={username}", status_code=303)


# ---------------------------------------------------------------------------
# File browser UI (session/memory/workspace/resources)
# ---------------------------------------------------------------------------


@app.get("/files/{root_name}", response_class=HTMLResponse)
async def browse_files(request: Request, root_name: str, path: str = Query(default=".")):
    root = _root(root_name)
    entries = fsops.list_files(root, path)
    return templates.TemplateResponse(
        request=request,
        name="files.html",
        context={
            "root_name": root_name,
            "roots": list(_ROOTS),
            "path": path,
            "entries": entries,
        },
    )


@app.get("/files/{root_name}/view", response_class=PlainTextResponse)
async def view_file(root_name: str, path: str = Query(...)):
    root = _root(root_name)
    try:
        return fsops.read_file(root, path)
    except (FileNotFoundError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/files/{root_name}/write")
async def write_file_route(root_name: str, path: str = Form(...), content: str = Form(...)):
    root = _root(root_name)
    fsops.write_file(root, path, content)
    parent = str(Path(path).parent)
    return RedirectResponse(url=f"/files/{root_name}?path={parent}", status_code=303)


@app.post("/files/{root_name}/upload")
async def upload_file_route(root_name: str, path: str = Form(default="."), file: UploadFile = None):
    root = _root(root_name)
    if file is None:
        raise HTTPException(status_code=400, detail="file is required")
    destination = str(Path(path) / file.filename)
    fsops.write_file_bytes(root, destination, await file.read())
    return RedirectResponse(url=f"/files/{root_name}?path={path}", status_code=303)


@app.post("/files/{root_name}/mkdir")
async def mkdir_route(root_name: str, path: str = Form(...), name: str = Form(...)):
    root = _root(root_name)
    fsops.make_dir(root, str(Path(path) / name))
    return RedirectResponse(url=f"/files/{root_name}?path={path}", status_code=303)


@app.post("/files/{root_name}/delete")
async def delete_file_route(root_name: str, path: str = Form(...), recursive: bool = Form(default=False)):
    root = _root(root_name)
    parent = str(Path(path).parent)
    fsops.delete_file(root, path, recursive=recursive)
    return RedirectResponse(url=f"/files/{root_name}?path={parent}", status_code=303)


@app.post("/files/{root_name}/move")
async def move_file_route(root_name: str, src: str = Form(...), dst: str = Form(...)):
    root = _root(root_name)
    fsops.move(root, src, dst)
    parent = str(Path(dst).parent)
    return RedirectResponse(url=f"/files/{root_name}?path={parent}", status_code=303)


# ---------------------------------------------------------------------------
# JSON API (for scripting)
# ---------------------------------------------------------------------------


@app.get("/api/sessions")
async def api_sessions(username: str = Query(...)):
    storage = _user_storage(username)
    return {"sessions": sessions_ops.list_sessions(Path(storage.session_folder))}


@app.get("/api/files/{root_name}")
async def api_list_files(root_name: str, path: str = Query(default=".")):
    root = _root(root_name)
    return {"entries": fsops.list_files(root, path)}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run("client.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
