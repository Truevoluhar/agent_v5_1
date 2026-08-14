"""FastAPI agent-runner service.

Runs the agent loop in-process (via agent.runner.AgentRunner) as a managed,
observable, cancellable run instead of a detached CLI subprocess. Exposes
three ways to consume the same run, per the recommended design:

- POST /api/runs:wait  - normal backend request, waits and returns final JSON
                         (falls back to a 202 + polling URLs if it's slow).
- POST /api/runs + GET /api/runs/{id}/events (SSE) - live browser chat.
- GET /api/runs/{id} (+ /events?after_sequence=N) - reconnect a long run.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agent.runner import RunRequest
from service import data_browser, event_store, run_registry

SERVICE_ROOT = Path(__file__).resolve().parent
WAIT_TIMEOUT_SECONDS = 300
SSE_POLL_INTERVAL_SECONDS = 0.3
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}

app = FastAPI(title="Agent Runner Service")
app.mount("/static", StaticFiles(directory=str(SERVICE_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(SERVICE_ROOT / "templates"))

event_store.init_db()


class RunRequestBody(BaseModel):
    username: str
    prompt: str
    workspace: Optional[str] = None
    session_id: Optional[str] = None
    response_schema: Optional[str] = None
    max_context_chars: Optional[int] = None


class RunInputBody(BaseModel):
    content: str


def _queued_response(handle: run_registry.RunHandle, status: str = "queued") -> dict:
    return {
        "run_id": handle.run_id,
        "session_id": handle.session_id,
        "status": status,
        "events_url": f"/api/runs/{handle.run_id}/events",
        "result_url": f"/api/runs/{handle.run_id}",
    }


def _run_status_payload(run_id: str) -> dict:
    run = event_store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    payload = dict(run)
    if payload.get("result_json"):
        payload["result"] = json.loads(payload["result_json"])
    return payload


@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request, username: str = "alice"):
    return templates.TemplateResponse(request=request, name="chat.html", context={"username": username})


@app.post("/api/runs")
async def create_run(body: RunRequestBody):
    request = RunRequest(**body.model_dump())
    handle = run_registry.start(request)
    return _queued_response(handle)


@app.post("/api/runs:wait")
async def run_and_wait(body: RunRequestBody):
    request = RunRequest(**body.model_dump())
    handle = run_registry.start(request)
    loop = asyncio.get_event_loop()

    try:
        result = await asyncio.wait_for(
            asyncio.shield(loop.run_in_executor(None, handle.result)),
            timeout=WAIT_TIMEOUT_SECONDS,
        )
        return {
            "run_id": handle.run_id,
            "session_id": handle.session_id,
            "status": result.status,
            "result": json.loads(result.final_response.model_dump_json()) if result.final_response is not None else None,
            "error": result.error,
        }
    except asyncio.TimeoutError:
        return JSONResponse(status_code=202, content=_queued_response(handle, status="running"))


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    return _run_status_payload(run_id)


@app.get("/api/sessions")
async def list_sessions(username: str):
    return {"sessions": data_browser.list_sessions(username)}


@app.get("/api/resources/prompts")
async def list_prompt_files():
    return {"files": data_browser.list_prompt_files()}


@app.get("/api/resources/prompts/{name}")
async def read_prompt_file(name: str):
    try:
        return {"name": name, "content": data_browser.read_prompt_file(name)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="prompt file not found")


@app.get("/api/resources/schemas")
async def list_response_schemas():
    return {"files": data_browser.list_response_schemas()}


@app.post("/api/runs/{run_id}/input")
async def submit_input(run_id: str, body: RunInputBody):
    if not run_registry.submit_input(run_id, body.content):
        raise HTTPException(status_code=404, detail="run not found or not accepting input in this process")
    return {"status": "accepted"}


@app.post("/api/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    if not run_registry.cancel(run_id):
        raise HTTPException(status_code=404, detail="run not found or not cancellable in this process")
    return {"status": "cancelling"}


def _sse_stream(run_id: str, after_sequence: int):
    last_sequence = after_sequence

    while True:
        events = event_store.get_events_after(run_id, last_sequence)
        for event in events:
            last_sequence = event["sequence"]
            yield f"id: {event['sequence']}\nevent: {event['type']}\ndata: {json.dumps(event)}\n\n"

        run = event_store.get_run(run_id)
        if run is None:
            break
        if run["status"] in TERMINAL_STATUSES and not events:
            yield (
                "event: stream.end\n"
                f"data: {json.dumps({'status': run['status'], 'error': run.get('error')})}\n\n"
            )
            break

        time.sleep(SSE_POLL_INTERVAL_SECONDS)


@app.get("/api/runs/{run_id}/events")
async def stream_events(run_id: str, after_sequence: int = 0):
    if event_store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    return StreamingResponse(_sse_stream(run_id, after_sequence), media_type="text/event-stream")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run("service.api:app", host="0.0.0.0", port=8100, reload=False)


if __name__ == "__main__":
    main()
