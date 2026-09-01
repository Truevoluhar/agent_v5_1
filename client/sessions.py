"""Read/write access to the shared bind-mounted session data.

This module talks to the sqlite session databases directly, using the same
schema as agent/session.py. It has no dependency on the agent package - the
client is a fully independent process that gives full read/write control
over session data (create, read, edit, delete sessions and messages).
"""
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT 'New chat',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_folder TEXT,
    memory_folder TEXT,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id
ON messages(session_id, id);
"""


def _connect(session_file: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(session_file)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(_SCHEMA)
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(sessions)").fetchall()
    }
    if "name" not in columns:
        connection.execute(
            "ALTER TABLE sessions ADD COLUMN name TEXT NOT NULL DEFAULT 'New chat'"
        )
    return connection


def _session_file(session_dir: Path, session_id: str) -> Path:
    return session_dir / f"session_{session_id}.sqlite3"


def list_sessions(session_dir: Path) -> List[Dict[str, Any]]:
    sessions: List[Dict[str, Any]] = []

    for session_file in sorted(session_dir.glob("session_*.sqlite3")):
        session_id = session_file.stem.replace("session_", "")
        try:
            with _connect(session_file) as connection:
                session_row = connection.execute(
                    "SELECT name, created_at, summary FROM sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
                message_count = connection.execute(
                    "SELECT COUNT(*) AS count FROM messages WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                last_message = connection.execute(
                    "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
        except sqlite3.Error:
            continue

        sessions.append(
            {
                "id": session_id,
                "name": session_row["name"] if session_row and session_row["name"] else "New chat",
                "path": str(session_file),
                "created_at": session_row["created_at"] if session_row else None,
                "summary": session_row["summary"] if session_row else None,
                "message_count": message_count["count"] if message_count else 0,
                "latest_role": last_message["role"] if last_message else None,
                "latest_content": last_message["content"] if last_message else None,
            }
        )

    sessions.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return sessions


def create_session(session_dir: Path, session_id: Optional[str] = None) -> str:
    session_dir.mkdir(parents=True, exist_ok=True)
    session_id = session_id or str(uuid.uuid4())
    session_file = _session_file(session_dir, session_id)

    with _connect(session_file) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO sessions (id) VALUES (?)",
            (session_id,),
        )

    return session_id


def read_session_messages(session_dir: Path, session_id: str) -> List[Dict[str, Any]]:
    session_file = _session_file(session_dir, session_id)
    if not session_file.is_file():
        raise FileNotFoundError(f"No such session: {session_id}")

    messages: List[Dict[str, Any]] = []
    with _connect(session_file) as connection:
        cursor = connection.execute(
            """
            SELECT id, payload
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
        for row in cursor.fetchall():
            try:
                decoded = json.loads(row["payload"])
            except json.JSONDecodeError:
                decoded = {"raw": row["payload"]}
            decoded["_message_id"] = row["id"]
            messages.append(decoded)

    return messages


def add_message(session_dir: Path, session_id: str, role: str, content: str) -> int:
    session_file = _session_file(session_dir, session_id)
    if not session_file.is_file():
        raise FileNotFoundError(f"No such session: {session_id}")

    message = {"role": role, "content": content}
    payload = json.dumps(message, ensure_ascii=False)

    with _connect(session_file) as connection:
        cursor = connection.execute(
            """
            INSERT INTO messages (session_id, role, content, payload)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, content, payload),
        )
        return cursor.lastrowid


def update_message(session_dir: Path, session_id: str, message_id: int, content: str) -> bool:
    session_file = _session_file(session_dir, session_id)
    if not session_file.is_file():
        raise FileNotFoundError(f"No such session: {session_id}")

    with _connect(session_file) as connection:
        row = connection.execute(
            "SELECT payload FROM messages WHERE session_id = ? AND id = ?",
            (session_id, message_id),
        ).fetchone()
        if row is None:
            return False

        try:
            payload = json.loads(row["payload"])
        except json.JSONDecodeError:
            payload = {}
        payload["content"] = content

        connection.execute(
            "UPDATE messages SET content = ?, payload = ? WHERE session_id = ? AND id = ?",
            (content, json.dumps(payload, ensure_ascii=False), session_id, message_id),
        )
        return True


def delete_message(session_dir: Path, session_id: str, message_id: int) -> bool:
    session_file = _session_file(session_dir, session_id)
    if not session_file.is_file():
        raise FileNotFoundError(f"No such session: {session_id}")

    with _connect(session_file) as connection:
        cursor = connection.execute(
            "DELETE FROM messages WHERE session_id = ? AND id = ?",
            (session_id, message_id),
        )
        return cursor.rowcount > 0


def set_summary(session_dir: Path, session_id: str, summary: str) -> bool:
    session_file = _session_file(session_dir, session_id)
    if not session_file.is_file():
        raise FileNotFoundError(f"No such session: {session_id}")

    with _connect(session_file) as connection:
        cursor = connection.execute(
            "UPDATE sessions SET summary = ? WHERE id = ?",
            (summary, session_id),
        )
        return cursor.rowcount > 0


def delete_session(session_dir: Path, session_id: str) -> bool:
    session_file = _session_file(session_dir, session_id)
    if not session_file.is_file():
        return False

    for suffix in ("", "-shm", "-wal"):
        candidate = session_file.with_name(session_file.name + suffix)
        if candidate.exists():
            candidate.unlink()

    return True
