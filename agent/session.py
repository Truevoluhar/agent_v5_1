import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List

from agent.semantic_memory import SemanticMemoryIndex


class Session:
    id: str
    session_folder: str
    workspace_folder: str
    memory_folder: str
    messages: list[dict]

    def __init__(
        self,
        session_folder: str,
        workspace_folder: str,
        memory_folder: str,
        id: str = None,
        messages: list[dict] = None,
    ):
        self.id = id if id is not None else str(uuid.uuid4())
        self.messages = []

        self.session_folder = str(Path(session_folder))
        self.workspace_folder = str(Path(workspace_folder))
        self.memory_folder = str(Path(memory_folder))

        self.db_path = Path(self.session_folder) / f"session_{self.id}.sqlite3"
        self.semantic_index = SemanticMemoryIndex(persist_path=self.memory_folder)

        self.create_session_folder()
        self.create_workspace_folder()
        self.create_folder(self.memory_folder)
        self._ensure_storage()

        if messages is not None:
            self._seed_messages(messages, replace_existing=True)

        if not self._has_session_record():
            self._insert_session_record()

        self.messages = self._load_messages_from_db()

    def _ensure_storage(self) -> None:
        self.create_session_folder()
        self.create_workspace_folder()
        self.create_folder(self.memory_folder)

        if not self.db_path.exists():
            self._open_connection().close()

        self._initialize_database()
        if not self._has_session_record():
            self._insert_session_record()

        legacy_jsonl_path = Path(self.session_folder) / f"session_{self.id}.jsonl"
        if legacy_jsonl_path.exists() and not self._has_message_rows():
            self._migrate_legacy_jsonl(legacy_jsonl_path)

    def _open_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize_database(self) -> None:
        with self._open_connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
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

                CREATE TABLE IF NOT EXISTS memory_summaries (
                    session_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id, id);
                """
            )

    def _has_session_record(self) -> bool:
        with self._open_connection() as connection:
            cursor = connection.execute(
                "SELECT 1 FROM sessions WHERE id = ?",
                (self.id,),
            )
            return cursor.fetchone() is not None

    def _has_message_rows(self) -> bool:
        with self._open_connection() as connection:
            cursor = connection.execute(
                "SELECT 1 FROM messages WHERE session_id = ? LIMIT 1",
                (self.id,),
            )
            return cursor.fetchone() is not None

    def _insert_session_record(self) -> None:
        with self._open_connection() as connection:
            connection.execute(
                """
                INSERT INTO sessions (id, workspace_folder, memory_folder, summary)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    workspace_folder = excluded.workspace_folder,
                    memory_folder = excluded.memory_folder,
                    summary = excluded.summary
                """,
                (self.id, self.workspace_folder, self.memory_folder, None),
            )

    def _load_messages_from_db(self) -> List[Dict[str, Any]]:
        with self._open_connection() as connection:
            cursor = connection.execute(
                """
                SELECT payload
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (self.id,),
            )
            rows = cursor.fetchall()

        messages: List[Dict[str, Any]] = []
        for row in rows:
            payload = row["payload"]
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                decoded = {"raw": payload}
            messages.append(decoded)

        return messages

    def _migrate_legacy_jsonl(self, legacy_path: Path) -> None:
        if not legacy_path.exists():
            return

        restored_messages: List[Dict[str, Any]] = []
        with legacy_path.open("r", encoding="utf-8") as file_obj:
            for line_num, line in enumerate(file_obj, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    restored_messages.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON on line {line_num} in {legacy_path}: {exc}"
                    ) from exc

        if restored_messages:
            self._seed_messages(restored_messages, replace_existing=False)

    def _seed_messages(
        self,
        messages: List[Dict[str, Any]],
        replace_existing: bool = False,
    ) -> None:
        if not messages:
            return

        with self._open_connection() as connection:
            if replace_existing:
                connection.execute(
                    "DELETE FROM messages WHERE session_id = ?",
                    (self.id,),
                )

            for message in messages:
                payload = json.dumps(message, ensure_ascii=False, default=str)
                role = str(message.get("role", "unknown"))
                content = message.get("content")
                connection.execute(
                    """
                    INSERT INTO messages (session_id, role, content, payload)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        self.id,
                        role,
                        content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str),
                        payload,
                    ),
                )

    def add_message(self, message: Dict[str, Any]) -> None:
        payload = json.dumps(message, ensure_ascii=False, default=str)
        content = message.get("content")

        with self._open_connection() as connection:
            connection.execute(
                """
                INSERT INTO messages (session_id, role, content, payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    self.id,
                    str(message.get("role", "unknown")),
                    content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str),
                    payload,
                ),
            )

        self.messages.append(message)

    def _fetch_recent_messages(self, max_recent_messages: int | None) -> List[Dict[str, Any]]:
        if max_recent_messages is None:
            return list(self.messages)
        return self.messages[-max_recent_messages:]

    def build_long_term_memory(self) -> str:
        with self._open_connection() as connection:
            cursor = connection.execute(
                "SELECT summary FROM memory_summaries WHERE session_id = ?",
                (self.id,),
            )
            row = cursor.fetchone()
            if row is not None and row["summary"]:
                return row["summary"]

        messages = self._load_messages_from_db()
        if not messages:
            return "No long-term memory available."

        last_messages = messages[-12:]
        summary_lines = []
        for item in last_messages:
            role = item.get("role", "unknown")
            content = item.get("content")
            if content:
                summary_lines.append(f"[{role}] {content}")

        summary_text = " | ".join(summary_lines)
        with self._open_connection() as connection:
            connection.execute(
                """
                INSERT INTO memory_summaries (session_id, summary)
                VALUES (?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    summary = excluded.summary,
                    created_at = CURRENT_TIMESTAMP
                """,
                (self.id, summary_text),
            )

        return summary_text

    def get_messages_for_agent(self, max_recent_messages: int | None = None) -> List[Dict[str, Any]]:
        self.messages = self._load_messages_from_db()

        if max_recent_messages is None:
            return list(self.messages)

        recent_messages = self._fetch_recent_messages(max_recent_messages)
        long_term_memory = self.build_long_term_memory()

        bounded_context = [
            {
                "role": "system",
                "content": f"Long-term memory: {long_term_memory}",
            },
            {
                "role": "system",
                "content": (
                    "Short-term memory: only the latest messages are kept in the active context "
                    "to avoid token growth across long tasks."
                ),
            },
            *recent_messages,
        ]

        return bounded_context

    def get_bounded_context(self, max_recent_messages: int = 12) -> List[Dict[str, Any]]:
        return self.get_messages_for_agent(max_recent_messages=max_recent_messages)

    def retrieve_past_sessions(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        session_dir = Path(self.session_folder)
        matching_rows: List[Dict[str, Any]] = []

        for session_file in sorted(session_dir.glob("session_*.sqlite3")):
            if session_file.name == f"session_{self.id}.sqlite3":
                continue

            with sqlite3.connect(session_file) as connection:
                cursor = connection.execute(
                    """
                    SELECT id, session_id, payload
                    FROM messages
                    WHERE payload LIKE ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (f"%{query}%", limit),
                )
                for row in cursor.fetchall():
                    matching_rows.append(
                        {
                            "session_id": row[1],
                            "message_id": row[0],
                            "payload": json.loads(row[2]),
                        }
                    )

        return matching_rows[:limit]

    def semantic_retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return self.semantic_index.search_sessions(
            session_dir=Path(self.session_folder),
            current_session_id=self.id,
            query=query,
            limit=limit,
        )

    def create_workspace_folder(self):
        try:
            Path(self.workspace_folder).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(e)

    def create_session_folder(self):
        try:
            Path(self.session_folder).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(e)

    def create_folder(self, folder):
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(e)

    def compact_memory(self):
        pass
