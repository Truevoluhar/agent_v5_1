import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

try:
    from chromadb import PersistentClient
except ImportError:  # pragma: no cover - fallback for environments without Chroma
    PersistentClient = None


class SemanticMemoryIndex:
    """A persistent, embedding-backed semantic index for session memory recall.

    The store is backed by Chroma's persistent client, which creates a browsable
    local vector database for historical session messages. Each message is stored
    with its session and row identifiers so cross-session retrieval can surface
    semantically similar context without needing to parse the entire transcript.
    """

    def __init__(self, persist_path: str | None = None, collection_name: str = "agent_session_memory"):
        self.persist_path = Path(persist_path or ".") / "chroma"
        self.collection_name = collection_name

        if PersistentClient is None:
            raise RuntimeError("chromadb is required for embedding-backed semantic memory")

        self.client = PersistentClient(path=str(self.persist_path))
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

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
                payload = json.loads(row["payload"])
                content = payload.get("content") if isinstance(payload, dict) else None
                if not content:
                    continue

                doc_id = f"{row['session_id']}::{row['id']}"
                existing = self.collection.get(ids=[doc_id], include=[])
                if existing and existing.get("ids"):
                    continue

                self.collection.add(
                    documents=[str(content)],
                    ids=[doc_id],
                    metadatas=[
                        {
                            "session_id": row["session_id"],
                            "message_id": row["id"],
                        }
                    ],
                )

    def _index_session_directory(self, session_dir: Path, current_session_id: str) -> None:
        self.persist_path.mkdir(parents=True, exist_ok=True)
        for session_file in sorted(session_dir.glob("session_*.sqlite3")):
            if session_file.name == f"session_{current_session_id}.sqlite3":
                continue
            self._index_session_file(session_file)

    def search_sessions(
        self,
        session_dir: Path,
        current_session_id: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        self._index_session_directory(session_dir, current_session_id)
        if not query:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        matches: List[Dict[str, Any]] = []
        for document, metadata, distance in zip(
            results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0],
            results.get("distances", [[]])[0],
        ):
            if not metadata:
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
