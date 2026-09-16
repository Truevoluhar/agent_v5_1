import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

try:
    from chromadb import PersistentClient
except ImportError:  # pragma: no cover - fallback for environments without Chroma
    PersistentClient = None


class SemanticMemoryIndex:
    """Optional Chroma index that never blocks durable session storage."""

    def __init__(self, persist_path: str | None = None, collection_name: str = "agent_session_memory"):
        self.persist_path = Path(persist_path or ".") / "chroma"
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.available = False
        self.disabled_reason: str | None = None

        mode = os.getenv("AGENT_SEMANTIC_MEMORY", "auto").strip().lower()
        if mode not in {"auto", "enabled", "disabled"}:
            raise ValueError("AGENT_SEMANTIC_MEMORY must be auto, enabled, or disabled")
        if mode == "disabled":
            self.disabled_reason = "disabled by AGENT_SEMANTIC_MEMORY"
            return

        if PersistentClient is None:
            self._disable("chromadb is not installed", warn=mode == "enabled")
            return

        try:
            self.client = PersistentClient(path=str(self.persist_path))
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            self.available = True
        except Exception as exc:
            self._disable(f"Chroma initialization failed: {type(exc).__name__}: {exc}")

    def _disable(self, reason: str, *, warn: bool = True) -> None:
        was_available = self.available
        self.available = False
        self.disabled_reason = reason
        if warn or was_available:
            logging.getLogger(__name__).warning(
                "Semantic memory unavailable; continuing with SQLite/lexical memory (%s)",
                reason,
            )

    def add_message(self, session_id: str, message_id: int, text: str) -> bool:
        if not text or not self.available or self.collection is None:
            return False

        try:
            doc_id = f"{session_id}::{message_id}"
            existing = self.collection.get(ids=[doc_id], include=[])
            if existing and existing.get("ids"):
                return True

            self.collection.add(
                documents=[text],
                ids=[doc_id],
                metadatas=[{"session_id": session_id, "message_id": message_id}],
            )
            return True
        except Exception as exc:
            # Chroma's default embedding function downloads an ONNX model on
            # first use. Offline/DNS/TLS failures must not abort the agent run.
            self._disable(f"embedding failed: {type(exc).__name__}: {exc}")
            return False

    def _index_session_file(self, session_file: Path) -> None:
        with sqlite3.connect(session_file) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, session_id, payload
                FROM messages
                ORDER BY id ASC
                """
            )

            for row in cursor.fetchall():
                if not self.available:
                    break
                payload = json.loads(row["payload"])
                content = payload.get("content") if isinstance(payload, dict) else None
                if not content:
                    continue

                self.add_message(
                    session_id=row["session_id"],
                    message_id=row["id"],
                    text=str(content),
                )

    def _index_session_directory(self, session_dir: Path, current_session_id: str) -> None:
        self.persist_path.mkdir(parents=True, exist_ok=True)
        current_session_file = session_dir / f"session_{current_session_id}.sqlite3"
        if current_session_file.exists():
            self._index_session_file(current_session_file)

    def search_sessions(
        self,
        session_dir: Path,
        current_session_id: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        if not self.available or self.collection is None:
            return []
        self._index_session_directory(session_dir, current_session_id)
        if not query or not self.available:
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            self._disable(f"semantic query failed: {type(exc).__name__}: {exc}")
            return []

        matches: List[Dict[str, Any]] = []
        for document, metadata, distance in zip(
            results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0],
            results.get("distances", [[]])[0],
        ):
            if not metadata:
                continue
            if metadata.get("session_id") != current_session_id:
                continue
            matches.append(
                {
                    "session_id": metadata.get("session_id"),
                    "message_id": metadata.get("message_id"),
                    "payload": {"content": document},
                    "score": float(distance),
                }
            )

        return matches
