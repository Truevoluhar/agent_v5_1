import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")


class SemanticMemoryIndex:
    """A lightweight vector-backed semantic index for session memory recall.

    The implementation intentionally avoids external ML packages and uses a
    deterministic bag-of-words hash embedding. Each normalized token is mapped
    to a stable vector slot using a hash function, after which cosine similarity
    is used to score stored messages against the current query.
    """

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        return [token.lower() for token in _TOKEN_PATTERN.findall(text)]

    def _stable_vector_slot(self, token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        value = int.from_bytes(digest[:8], byteorder="big", signed=False)
        return value % self.dimensions

    def _embed_text(self, text: str) -> List[float]:
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dimensions

        counts = Counter(tokens)
        vector = [0.0] * self.dimensions
        for token, count in counts.items():
            slot = self._stable_vector_slot(token)
            vector[slot] += float(count)

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0.0:
            return vector

        return [value / magnitude for value in vector]

    def _cosine_similarity(self, left: Sequence[float], right: Sequence[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def search_sessions(
        self,
        session_dir: Path,
        current_session_id: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        query_text = query or ""
        query_vector = self._embed_text(query_text)
        rankings: List[Tuple[float, Dict[str, Any]]] = []

        for session_file in sorted(session_dir.glob("session_*.sqlite3")):
            if session_file.name == f"session_{current_session_id}.sqlite3":
                continue

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
                    candidate_vector = self._embed_text(str(content))
                    score = self._cosine_similarity(query_vector, candidate_vector)
                    rankings.append(
                        (
                            score,
                            {
                                "session_id": row["session_id"],
                                "message_id": row["id"],
                                "payload": payload,
                                "score": score,
                            },
                        )
                    )

        rankings.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in rankings[:limit]]
