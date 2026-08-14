"""Persistent run/event storage shared by the agent-api service.

Schema matches the PDF's recommended layout so runs remain resumable/
reconnectable (GET /api/runs/{id}/events?after_sequence=N) even across
service restarts.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.events import RunEvent
from agent.paths import DATA_ROOT

DB_PATH = DATA_ROOT / "runs" / "runs.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    username TEXT NOT NULL,
    status TEXT NOT NULL,
    prompt TEXT NOT NULL,
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, sequence)
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    # Idempotent: guards against the db file being deleted/recreated (e.g. a
    # bind-mounted data/ directory wiped) while the service keeps running.
    connection.executescript(_SCHEMA)
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.executescript(_SCHEMA)


def create_run(run_id: str, session_id: str, username: str, prompt: str) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO runs (id, session_id, username, status, prompt, created_at)
            VALUES (?, ?, ?, 'queued', ?, datetime('now'))
            """,
            (run_id, session_id, username, prompt),
        )


def mark_started(run_id: str) -> None:
    with _connect() as connection:
        connection.execute(
            "UPDATE runs SET status = 'running', started_at = COALESCE(started_at, datetime('now')) WHERE id = ?",
            (run_id,),
        )


def mark_status(run_id: str, status: str) -> None:
    with _connect() as connection:
        connection.execute("UPDATE runs SET status = ? WHERE id = ?", (status, run_id))


def mark_completed(
    run_id: str,
    status: str,
    result_json: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    with _connect() as connection:
        connection.execute(
            """
            UPDATE runs
            SET status = ?, result_json = ?, error = ?, completed_at = datetime('now')
            WHERE id = ?
            """,
            (status, result_json, error, run_id),
        )


def append_event(event: RunEvent) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO run_events (run_id, sequence, event_type, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event.run_id,
                event.sequence,
                event.type,
                json.dumps(event.data, ensure_ascii=False, default=str),
                event.created_at,
            ),
        )


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None


def get_events_after(run_id: str, after_sequence: int = 0) -> List[Dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT sequence, event_type, payload, created_at
            FROM run_events
            WHERE run_id = ? AND sequence > ?
            ORDER BY sequence ASC
            """,
            (run_id, after_sequence),
        ).fetchall()

    events: List[Dict[str, Any]] = []
    for row in rows:
        try:
            data = json.loads(row["payload"])
        except json.JSONDecodeError:
            data = {"raw": row["payload"]}
        events.append(
            {
                "sequence": row["sequence"],
                "type": row["event_type"],
                "data": data,
                "created_at": row["created_at"],
            }
        )
    return events
