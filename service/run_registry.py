""" Manages active/background agent runs: one worker thread per run, an input
queue for ask_user-style prompts, and a cancellation flag - all bridged to
durable storage in event_store so runs are observable via HTTP even from a
different process than the one that started them (as long as they're both
talking to the same run_registry instance).
"""
from __future__ import annotations

import logging
import queue
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

from agent.events import RunEvent
from agent.runner import AgentRunner, RunRequest, RunResult
from service import event_store

logger = logging.getLogger("service.run_registry")

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="agent-run")
_runner = AgentRunner()

_runs: dict[str, "RunHandle"] = {}
_runs_lock = threading.Lock()


@dataclass
class RunHandle:
    run_id: str
    session_id: str
    future: Optional[Future] = None
    input_queue: "queue.Queue[str]" = field(default_factory=queue.Queue)
    cancel_event: threading.Event = field(default_factory=threading.Event)

    def result(self, timeout: Optional[float] = None) -> RunResult:
        return self.future.result(timeout=timeout)


def _execute(handle: RunHandle, request: RunRequest) -> RunResult:
    event_store.mark_started(handle.run_id)

    def emit(event: RunEvent) -> None:
        event_store.append_event(event)
        if event.type == "input.required":
            event_store.mark_status(handle.run_id, "waiting_for_input")
        elif event.type in ("orchestrator.started", "agent.delegated"):
            event_store.mark_status(handle.run_id, "running")

    def wait_for_input(question: str) -> str:
        return handle.input_queue.get()

    def is_cancelled() -> bool:
        return handle.cancel_event.is_set()

    # This runs on a worker thread with nobody awaiting its Future, so any
    # exception - even one raised before AgentRunner.run() sets up its own
    # emitter/try-except (e.g. bad config, missing resource files) - must be
    # caught here. Otherwise it's silently swallowed by the executor, the run
    # stays stuck at 'running' forever, and the caller never finds out why.
    try:
        result = _runner.run(request, emit=emit, wait_for_input=wait_for_input, is_cancelled=is_cancelled)
    except Exception as exc:
        logger.exception("Run %s crashed before completion", handle.run_id)
        event_store.mark_completed(handle.run_id, "failed", error=f"{type(exc).__name__}: {exc}")
        return RunResult(run_id=handle.run_id, session_id=handle.session_id, status="failed", error=str(exc))

    event_store.mark_completed(
        handle.run_id,
        result.status,
        result_json=result.final_response.model_dump_json() if result.final_response is not None else None,
        error=result.error,
    )
    return result


def start(request: RunRequest) -> RunHandle:
    run_id = request.run_id or str(uuid.uuid4())
    request.run_id = run_id

    # Pre-resolve the session id (Session would otherwise generate its own)
    # so the run row/events can reference it deterministically up front.
    session_id = request.session_id or str(uuid.uuid4())
    request.session_id = session_id

    event_store.create_run(run_id, session_id, request.username, request.prompt)

    handle = RunHandle(run_id=run_id, session_id=session_id)
    handle.future = _executor.submit(_execute, handle, request)

    with _runs_lock:
        _runs[run_id] = handle

    return handle


def get(run_id: str) -> Optional[RunHandle]:
    with _runs_lock:
        return _runs.get(run_id)


def submit_input(run_id: str, content: str) -> bool:
    handle = get(run_id)
    if handle is None:
        return False
    handle.input_queue.put(content)
    return True


def cancel(run_id: str) -> bool:
    handle = get(run_id)
    if handle is None:
        return False
    handle.cancel_event.set()
    return True
