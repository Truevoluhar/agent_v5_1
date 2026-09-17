"""Durable SQLite task board used by the orchestrator and delegated agents."""
from __future__ import annotations

from contextlib import contextmanager
import codecs
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {"validated", "cancelled"}


def workspace_file(workspace: str | Path, name: str) -> Path:
    root = Path(workspace).resolve()
    path = (root / name).resolve()
    if path != root and root not in path.parents:
        raise ValueError("Path must stay inside the workspace")
    return path


def digest(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class TaskBoard:
    """SQLite-backed task state for orchestration, delegation, and validation."""

    def __init__(self, workspace: str | Path, scope: str = "default"):
        self.root = Path(workspace).resolve()
        directory = workspace_file(self.root, ".agent/tasks")
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / (hashlib.sha256(scope.encode("utf-8")).hexdigest() + ".sqlite3")
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS context (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    task_key TEXT NOT NULL UNIQUE,
                    parent_task_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    task_type TEXT NOT NULL DEFAULT 'implementation',
                    priority INTEGER NOT NULL DEFAULT 50,
                    status TEXT NOT NULL DEFAULT 'pending',
                    suggested_agent TEXT,
                    assigned_agent TEXT,
                    delegation_instructions TEXT,
                    depends_on_keys TEXT NOT NULL DEFAULT '[]',
                    acceptance_criteria TEXT NOT NULL DEFAULT '[]',
                    artifacts TEXT NOT NULL DEFAULT '[]',
                    result_summary TEXT,
                    evidence TEXT,
                    validation_notes TEXT,
                    follow_up_suggestions TEXT,
                    created_by TEXT,
                    last_error TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    started_at TEXT,
                    reported_at TEXT,
                    validated_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY(parent_task_id) REFERENCES tasks(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER,
                    event_type TEXT NOT NULL,
                    agent_name TEXT,
                    summary TEXT NOT NULL,
                    payload TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
                ON tasks(status, priority, id);

                CREATE INDEX IF NOT EXISTS idx_task_events_task
                ON task_events(task_id, id);
                """
            )
            self._ensure_task_columns(db)
        self._refresh_ready_states()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _loads_list(raw: str | None) -> list[Any]:
        if not raw:
            return []
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return value if isinstance(value, list) else []

    @staticmethod
    def _ensure_task_columns(db: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in db.execute("PRAGMA table_info(tasks)").fetchall()
        }
        additions = {
            "source_path": "TEXT",
            "source_hash": "TEXT",
            "source_cursor": "INTEGER NOT NULL DEFAULT 0",
            "source_encoding": "TEXT",
        }
        for column, ddl in additions.items():
            if column not in columns:
                db.execute(f"ALTER TABLE tasks ADD COLUMN {column} {ddl}")

    def _normalize_task(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        for field in ("depends_on_keys", "acceptance_criteria", "artifacts"):
            item[field] = self._loads_list(item.get(field))
        return item

    def _record_event(
        self,
        db: sqlite3.Connection,
        *,
        event_type: str,
        summary: str,
        task_id: int | None = None,
        agent_name: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        db.execute(
            """
            INSERT INTO task_events (task_id, event_type, agent_name, summary, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                task_id,
                event_type,
                agent_name,
                summary,
                json.dumps(payload or {}, ensure_ascii=False, default=str),
            ),
        )

    @staticmethod
    def _is_excluded_path(relative: Path) -> bool:
        return any(part in {".agent", ".git", "node_modules", "venv", "__pycache__"} for part in relative.parts)

    @staticmethod
    def _detect_text_encoding(raw: bytes) -> str | None:
        if not raw:
            return "utf-8"
        if b"\x00" in raw[:4096]:
            return None
        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                raw.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        return "latin-1"

    def _refresh_ready_states(self) -> None:
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, status, depends_on_keys FROM tasks WHERE status IN ('pending', 'ready')"
            ).fetchall()
            for row in rows:
                deps = self._loads_list(row["depends_on_keys"])
                if not deps:
                    desired = "ready"
                else:
                    placeholders = ",".join("?" for _ in deps)
                    dep_rows = db.execute(
                        f"SELECT task_key, status FROM tasks WHERE task_key IN ({placeholders})",
                        tuple(deps),
                    ).fetchall()
                    statuses = {dep["task_key"]: dep["status"] for dep in dep_rows}
                    desired = (
                        "ready"
                        if all(statuses.get(dep) in TERMINAL_STATUSES for dep in deps)
                        else "pending"
                    )
                if row["status"] != desired:
                    db.execute(
                        "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (desired, row["id"]),
                    )

    def has_tasks(self) -> bool:
        with self.connect() as db:
            row = db.execute("SELECT 1 FROM tasks LIMIT 1").fetchone()
        return row is not None

    def total_tasks(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT count(*) AS n FROM tasks").fetchone()
        return int(row["n"]) if row else 0

    def objective(self, prompt: str) -> str:
        with self.connect() as db:
            row = db.execute("SELECT value FROM context WHERE key='objective'").fetchone()
            if row is None:
                value = prompt
                db.execute(
                    "INSERT INTO context(key, value) VALUES('objective', ?)",
                    (value,),
                )
            else:
                value = row["value"]
                if prompt and prompt not in value:
                    value = value + "\nCurrent follow-up: " + prompt
                    db.execute(
                        "UPDATE context SET value = ? WHERE key='objective'",
                        (value,),
                    )
        return value

    @staticmethod
    def _unique_key(task_key: str, existing: set[str]) -> str:
        base = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in task_key.upper())
        base = base.strip("-") or "TASK"
        if base not in existing:
            return base
        suffix = 2
        while f"{base}-{suffix}" in existing:
            suffix += 1
        return f"{base}-{suffix}"

    def add_tasks(self, tasks: list[dict[str, Any]], created_by: str = "orchestrator") -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        with self.connect() as db:
            existing_keys = {
                row["task_key"] for row in db.execute("SELECT task_key FROM tasks").fetchall()
            }
            for task in tasks:
                task_key = str(task.get("task_key") or task.get("title") or "TASK").strip()
                if not task_key:
                    raise ValueError("Task key is required")
                task_key = self._unique_key(task_key, existing_keys)
                existing_keys.add(task_key)
                depends_on_keys = [
                    str(item).strip()
                    for item in (task.get("depends_on_keys") or [])
                    if str(item).strip()
                ]
                acceptance_criteria = [
                    str(item).strip()
                    for item in (task.get("acceptance_criteria") or [])
                    if str(item).strip()
                ]
                source_path = str(task.get("source_path") or "").strip() or None
                source_hash = None
                source_encoding = None
                if source_path:
                    path = workspace_file(self.root, source_path)
                    if not path.is_file():
                        raise ValueError(f"Source file not found: {source_path}")
                    source_hash = digest(path)
                    source_encoding = self._detect_text_encoding(path.read_bytes()[:32768])
                priority = int(task.get("priority", 50))
                cursor = db.execute(
                    """
                    INSERT INTO tasks (
                        task_key, parent_task_id, title, description, task_type, priority,
                        status, suggested_agent, depends_on_keys, acceptance_criteria,
                        created_by, source_path, source_hash, source_cursor, source_encoding
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        task_key,
                        task.get("parent_task_id"),
                        str(task.get("title") or task_key),
                        str(task.get("description") or ""),
                        str(task.get("task_type") or "implementation"),
                        priority,
                        task.get("suggested_agent"),
                        json.dumps(depends_on_keys, ensure_ascii=False),
                        json.dumps(acceptance_criteria, ensure_ascii=False),
                        created_by,
                        source_path,
                        source_hash,
                        source_encoding,
                    ),
                )
                task_id = int(cursor.lastrowid)
                created_task = {
                    "id": task_id,
                    "task_key": task_key,
                    "title": str(task.get("title") or task_key),
                    "description": str(task.get("description") or ""),
                    "task_type": str(task.get("task_type") or "implementation"),
                    "priority": priority,
                    "suggested_agent": task.get("suggested_agent"),
                    "depends_on_keys": depends_on_keys,
                    "acceptance_criteria": acceptance_criteria,
                    "source_path": source_path,
                    "source_encoding": source_encoding,
                }
                created.append(created_task)
                self._record_event(
                    db,
                    task_id=task_id,
                    event_type="task.created",
                    agent_name=created_by,
                    summary=f"Created task {task_key}: {created_task['title']}",
                    payload=created_task,
                )
        self._refresh_ready_states()
        return created

    def inventory(
        self,
        *,
        root: str,
        pattern: str,
        task_type: str,
        title_prefix: str,
        description_template: str,
        acceptance_criteria: list[str],
        suggested_agent: str | None = None,
        priority: int = 50,
        created_by: str = "orchestrator",
        parent_task_id: int | None = None,
    ) -> dict[str, Any]:
        base = workspace_file(self.root, root or ".")
        if not base.is_dir():
            raise ValueError("Inventory root must be a directory")

        created: list[dict[str, Any]] = []
        seen: set[str] = set()
        for path in sorted(base.glob(pattern or "**/*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(self.root)
            if self._is_excluded_path(relative):
                continue
            if str(relative) in seen:
                continue
            seen.add(str(relative))
            created.append(
                {
                    "task_key": f"FILE-{relative.as_posix().replace('/', '-').replace('.', '_')}",
                    "parent_task_id": parent_task_id,
                    "title": f"{title_prefix} {relative.as_posix()}",
                    "description": description_template.format(source_path=relative.as_posix()),
                    "task_type": task_type,
                    "priority": priority,
                    "suggested_agent": suggested_agent,
                    "acceptance_criteria": acceptance_criteria,
                    "source_path": relative.as_posix(),
                }
            )

        with self.connect() as db:
            existing_sources = {
                row["source_path"]
                for row in db.execute(
                    "SELECT source_path FROM tasks WHERE source_path IS NOT NULL"
                ).fetchall()
            }
        filtered = [task for task in created if task["source_path"] not in existing_sources]
        added = self.add_tasks(filtered, created_by=created_by) if filtered else []
        return {"added": len(added), "discovered": len(created), "summary": self.summary()}

    def list_tasks(self, statuses: list[str] | None = None, limit: int = 20) -> list[dict[str, Any]]:
        self._refresh_ready_states()
        with self.connect() as db:
            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                rows = db.execute(
                    f"""
                    SELECT *
                    FROM tasks
                    WHERE status IN ({placeholders})
                    ORDER BY priority ASC, id ASC
                    LIMIT ?
                    """,
                    (*statuses, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    """
                    SELECT *
                    FROM tasks
                    ORDER BY
                        CASE status
                            WHEN 'in_progress' THEN 0
                            WHEN 'reported' THEN 1
                            WHEN 'ready' THEN 2
                            WHEN 'pending' THEN 3
                            WHEN 'blocked' THEN 4
                            WHEN 'validated' THEN 5
                            ELSE 6
                        END,
                        priority ASC,
                        id ASC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [self._normalize_task(row) for row in rows]

    def get_task(self, task_id: int | None = None, task_key: str | None = None) -> dict[str, Any] | None:
        if task_id is None and task_key is None:
            raise ValueError("task_id or task_key is required")
        with self.connect() as db:
            if task_id is not None:
                row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            else:
                row = db.execute("SELECT * FROM tasks WHERE task_key = ?", (task_key,)).fetchone()
        return self._normalize_task(row)

    def next_ready(self) -> dict[str, Any] | None:
        self._refresh_ready_states()
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM tasks WHERE status = 'ready' ORDER BY priority ASC, id ASC LIMIT 1"
            ).fetchone()
        return self._normalize_task(row)

    def active_task(self, agent_name: str | None = None) -> dict[str, Any] | None:
        with self.connect() as db:
            if agent_name:
                row = db.execute(
                    """
                    SELECT *
                    FROM tasks
                    WHERE status = 'in_progress' AND assigned_agent = ?
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                    (agent_name,),
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT * FROM tasks WHERE status = 'in_progress' ORDER BY id ASC LIMIT 1"
                ).fetchone()
        return self._normalize_task(row)

    def begin_task(self, task_id: int, agent_name: str, instructions: str) -> dict[str, Any]:
        self._refresh_ready_states()
        with self.connect() as db:
            row = db.execute(
                "SELECT status, task_key, source_path FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Unknown task")
            if row["status"] != "ready":
                raise ValueError(f"Task {task_id} is not ready; current status is {row['status']}")
            db.execute(
                """
                UPDATE tasks
                SET status = 'in_progress',
                    assigned_agent = ?,
                    delegation_instructions = ?,
                    attempt_count = attempt_count + 1,
                    source_cursor = 0,
                    source_encoding = CASE
                        WHEN source_path IS NULL THEN source_encoding
                        ELSE NULL
                    END,
                    started_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    last_error = NULL
                WHERE id = ?
                """,
                (agent_name, instructions, task_id),
            )
            self._record_event(
                db,
                task_id=task_id,
                event_type="task.assigned",
                agent_name=agent_name,
                summary=f"Assigned {row['task_key']} to {agent_name}",
                payload={"instructions": instructions},
            )
        return self.get_task(task_id=task_id) or {}

    def read_source(self, task_id: int, max_chars: int = 4000) -> dict[str, Any]:
        if not 4 <= max_chars <= 12000:
            raise ValueError("max_chars must be between 4 and 12000")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """
                SELECT id, status, source_path, source_hash, source_cursor, source_encoding
                FROM tasks
                WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Unknown task")
            if row["status"] not in {"in_progress", "reported"}:
                raise ValueError("Task must be in_progress or reported before reading its source")
            source_path = row["source_path"]
            if not source_path:
                raise ValueError("Task has no source file")
            path = workspace_file(self.root, source_path)
            if not path.is_file():
                raise ValueError(f"Source file not found: {source_path}")
            if row["source_cursor"] == 0 and row["source_hash"] and digest(path) != row["source_hash"]:
                raise ValueError("Source changed since task creation; reopen the task to refresh it")
            encoding = row["source_encoding"]
            if not encoding:
                encoding = self._detect_text_encoding(path.read_bytes()[:32768])
                if not encoding:
                    raise ValueError("Binary or unsupported text file; cannot read source as text")
                db.execute(
                    "UPDATE tasks SET source_encoding = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (encoding, task_id),
                )
            with path.open("rb") as stream:
                stream.seek(int(row["source_cursor"] or 0))
                chunk = stream.read(max_chars)
                decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
                content = decoder.decode(chunk, final=stream.tell() == path.stat().st_size)
                end = stream.tell() - len(decoder.getstate()[0])
            db.execute(
                "UPDATE tasks SET source_cursor = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (end, task_id),
            )
            return {
                "source_path": source_path,
                "offset": int(row["source_cursor"] or 0),
                "next_offset": end,
                "eof": end == path.stat().st_size,
                "content": content,
                "encoding": encoding,
            }

    def _artifact_records(self, artifacts: list[str]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for name in artifacts:
            normalized = str(name).strip()
            if not normalized:
                continue
            path = workspace_file(self.root, normalized)
            if not path.exists():
                raise ValueError(f"Artifact not found: {normalized}")
            validation_mode = "exists"
            if path.is_file() and path.parts and ".agent" in path.parts:
                validation_mode = "sha256"
            records.append(
                {
                    "path": normalized,
                    "sha256": digest(path) if path.is_file() else None,
                    "validation_mode": validation_mode,
                }
            )
        return records

    def submit(
        self,
        task_id: int,
        *,
        summary: str,
        evidence: str,
        artifacts: list[str],
        follow_up_suggestions: str = "",
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        if not summary.strip():
            raise ValueError("Task summary is required")
        if not evidence.strip():
            raise ValueError("Task evidence is required")
        records = self._artifact_records(artifacts)
        with self.connect() as db:
            row = db.execute(
                "SELECT status, assigned_agent, task_key, source_path, source_hash, source_cursor FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Unknown task")
            if row["status"] not in {"in_progress", "reported"}:
                raise ValueError("Task must be in_progress or already reported before it can be submitted")
            if agent_name and row["assigned_agent"] and row["assigned_agent"] != agent_name:
                raise ValueError("Only the assigned agent may submit this task")
            if row["source_path"]:
                path = workspace_file(self.root, row["source_path"])
                if not path.is_file():
                    raise ValueError(f"Source file not found: {row['source_path']}")
                if row["source_hash"] and digest(path) != row["source_hash"]:
                    raise ValueError("Source changed since task creation; reopen the task to refresh it")
                if int(row["source_cursor"] or 0) < path.stat().st_size:
                    raise ValueError("Read the full source before submitting this file task")
            db.execute(
                """
                UPDATE tasks
                SET status = 'reported',
                    result_summary = ?,
                    evidence = ?,
                    artifacts = ?,
                    follow_up_suggestions = ?,
                    reported_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    summary,
                    evidence,
                    json.dumps(records, ensure_ascii=False),
                    follow_up_suggestions,
                    task_id,
                ),
            )
            self._record_event(
                db,
                task_id=task_id,
                event_type="task.reported",
                agent_name=agent_name or row["assigned_agent"],
                summary=f"Worker submitted task {row['task_key']}",
                payload={
                    "summary": summary,
                    "evidence": evidence,
                    "artifacts": records,
                    "follow_up_suggestions": follow_up_suggestions,
                },
            )
        return self.get_task(task_id=task_id) or {}

    def block(self, task_id: int, reason: str, agent_name: str | None = None) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("Block reason is required")
        with self.connect() as db:
            row = db.execute(
                "SELECT status, assigned_agent, task_key FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Unknown task")
            if row["status"] not in {"ready", "in_progress", "reported"}:
                raise ValueError("Only ready, in_progress, or reported tasks can be blocked")
            db.execute(
                """
                UPDATE tasks
                SET status = 'blocked',
                    last_error = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (reason, task_id),
            )
            self._record_event(
                db,
                task_id=task_id,
                event_type="task.blocked",
                agent_name=agent_name or row["assigned_agent"],
                summary=f"Task {row['task_key']} blocked",
                payload={"reason": reason},
            )
        return self.get_task(task_id=task_id) or {}

    def reopen(self, task_id: int, notes: str = "") -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT status, task_key, source_path, source_encoding FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Unknown task")
            if row["status"] in TERMINAL_STATUSES:
                raise ValueError("Validated or cancelled tasks cannot be reopened")
            db.execute(
                """
                UPDATE tasks
                SET status = 'pending',
                    validation_notes = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    assigned_agent = NULL,
                    delegation_instructions = NULL,
                    source_hash = CASE
                        WHEN source_path IS NULL THEN source_hash
                        ELSE ?
                    END,
                    source_cursor = 0,
                    source_encoding = CASE
                        WHEN source_path IS NULL THEN source_encoding
                        ELSE ?
                    END
                WHERE id = ?
                """,
                (
                    notes or None,
                    digest(workspace_file(self.root, row["source_path"])) if row["source_path"] else None,
                    self._detect_text_encoding(workspace_file(self.root, row["source_path"]).read_bytes()[:32768])
                    if row["source_path"] else None,
                    task_id,
                ),
            )
            self._record_event(
                db,
                task_id=task_id,
                event_type="task.reopened",
                summary=f"Task {row['task_key']} reopened",
                payload={"notes": notes},
            )
        self._refresh_ready_states()
        return self.get_task(task_id=task_id) or {}

    def validate(
        self,
        task_id: int,
        *,
        accepted: bool,
        validation_notes: str,
    ) -> dict[str, Any]:
        if not validation_notes.strip():
            raise ValueError("Validation notes are required")
        with self.connect() as db:
            row = db.execute(
                "SELECT status, task_key FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Unknown task")
            if accepted:
                if row["status"] != "reported":
                    raise ValueError("Only reported tasks can be validated")
                db.execute(
                    """
                    UPDATE tasks
                    SET status = 'validated',
                        validation_notes = ?,
                        validated_at = CURRENT_TIMESTAMP,
                        completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP,
                        last_error = NULL
                    WHERE id = ?
                    """,
                    (validation_notes, task_id),
                )
                event_type = "task.validated"
                summary = f"Task {row['task_key']} validated"
            else:
                if row["status"] not in {"reported", "blocked", "in_progress"}:
                    raise ValueError("Only active or reported tasks can be returned for rework")
                db.execute(
                    """
                    UPDATE tasks
                    SET status = 'pending',
                        validation_notes = ?,
                        updated_at = CURRENT_TIMESTAMP,
                        assigned_agent = NULL,
                        delegation_instructions = NULL,
                        last_error = NULL
                    WHERE id = ?
                    """,
                    (validation_notes, task_id),
                )
                event_type = "task.rework_requested"
                summary = f"Task {row['task_key']} returned for rework"
            self._record_event(
                db,
                task_id=task_id,
                event_type=event_type,
                summary=summary,
                payload={"accepted": accepted, "validation_notes": validation_notes},
            )
        self._refresh_ready_states()
        return self.get_task(task_id=task_id) or {}

    def cancel(self, task_id: int, reason: str) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("Cancellation reason is required")
        with self.connect() as db:
            row = db.execute(
                "SELECT task_key FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Unknown task")
            db.execute(
                """
                UPDATE tasks
                SET status = 'cancelled',
                    validation_notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (reason, task_id),
            )
            self._record_event(
                db,
                task_id=task_id,
                event_type="task.cancelled",
                summary=f"Task {row['task_key']} cancelled",
                payload={"reason": reason},
            )
        self._refresh_ready_states()
        return self.get_task(task_id=task_id) or {}

    def summary(self, limit: int = 8) -> dict[str, Any]:
        self._refresh_ready_states()
        with self.connect() as db:
            counts = {
                row["status"]: row["n"]
                for row in db.execute("SELECT status, count(*) AS n FROM tasks GROUP BY status").fetchall()
            }
            remaining = sum(count for status, count in counts.items() if status not in TERMINAL_STATUSES)
            next_ready = [
                self._normalize_task(row)
                for row in db.execute(
                    "SELECT * FROM tasks WHERE status = 'ready' ORDER BY priority ASC, id ASC LIMIT ?",
                    (limit,),
                ).fetchall()
            ]
            active = [
                self._normalize_task(row)
                for row in db.execute(
                    "SELECT * FROM tasks WHERE status = 'in_progress' ORDER BY priority ASC, id ASC LIMIT ?",
                    (limit,),
                ).fetchall()
            ]
            review = [
                self._normalize_task(row)
                for row in db.execute(
                    "SELECT * FROM tasks WHERE status IN ('reported', 'blocked') ORDER BY priority ASC, id ASC LIMIT ?",
                    (limit,),
                ).fetchall()
            ]
        return {
            "total": sum(counts.values()),
            "counts": counts,
            "remaining": remaining,
            "next_ready": next_ready,
            "active": active,
            "review": review,
        }

    def recent_activity(self, limit: int = 10) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT task_id, event_type, agent_name, summary, payload, created_at
                FROM task_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        activity: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["payload"] = json.loads(item["payload"])
            except json.JSONDecodeError:
                item["payload"] = {}
            activity.append(item)
        return activity

    def verify(self) -> dict[str, Any]:
        invalidated: list[int] = []
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, artifacts FROM tasks WHERE status = 'validated'"
            ).fetchall()
            for row in rows:
                try:
                    for artifact in self._loads_list(row["artifacts"]):
                        if not isinstance(artifact, dict):
                            continue
                        path = workspace_file(self.root, str(artifact.get("path", "")))
                        if not path.exists():
                            raise ValueError("Artifact missing")
                        sha = artifact.get("sha256")
                        validation_mode = artifact.get("validation_mode") or "exists"
                        if validation_mode == "sha256" and sha and path.is_file() and digest(path) != sha:
                            raise ValueError("Artifact changed")
                except (OSError, ValueError) as exc:
                    invalidated.append(int(row["id"]))
                    db.execute(
                        """
                        UPDATE tasks
                        SET status = 'blocked',
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (str(exc), row["id"]),
                    )
                    self._record_event(
                        db,
                        task_id=int(row["id"]),
                        event_type="task.invalidated",
                        summary=f"Validated task {row['id']} invalidated",
                        payload={"error": str(exc)},
                    )
        return {"invalidated": invalidated, **self.summary()}

    def completion_report(self) -> dict[str, Any]:
        with self.connect() as db:
            rows = [
                self._normalize_task(row)
                for row in db.execute(
                    """
                    SELECT id, task_key, title, description, task_type, assigned_agent,
                           result_summary, evidence, validation_notes, artifacts
                    FROM tasks
                    WHERE status = 'validated'
                    ORDER BY priority ASC, id ASC
                    """
                ).fetchall()
            ]
        report_path = self.path.with_suffix(".report.json")
        report_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        artifact_paths = sorted(
            {
                str(artifact.get("path"))
                for row in rows
                for artifact in (row.get("artifacts") or [])
                if isinstance(artifact, dict) and artifact.get("path")
            }
        )
        return {
            "validated_tasks": len(rows),
            "artifact_count": len(artifact_paths),
            "artifact_paths": artifact_paths[:25],
            "paths_truncated": len(artifact_paths) > 25,
            "full_report": str(report_path.relative_to(self.root)),
            "tasks": rows[:10],
            "tasks_truncated": len(rows) > 10,
        }


WorkQueue = TaskBoard
