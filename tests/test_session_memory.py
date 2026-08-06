import tempfile
import unittest
from pathlib import Path
from types import MethodType

from agent.session import Session


class SessionMemoryTests(unittest.TestCase):

    def test_short_term_and_long_term_memory_are_bounded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            session_dir = temp_path / "session"
            workspace_dir = temp_path / "workspace"
            memory_dir = temp_path / "memory"

            session_dir.mkdir()
            workspace_dir.mkdir()
            memory_dir.mkdir()

            session = Session(
                session_folder=str(session_dir),
                workspace_folder=str(workspace_dir),
                memory_folder=str(memory_dir),
            )

            for idx in range(20):
                session.add_message({"role": "user", "content": f"task {idx}"})
                session.add_message({"role": "assistant", "content": f"result {idx}"})

            context = session.get_messages_for_agent(max_recent_messages=4)

            self.assertLessEqual(len(context), 6)
            self.assertTrue(any(msg.get("role") == "system" and "Long-term memory" in msg.get("content", "") for msg in context))
            self.assertEqual(context[-1]["content"], "result 19")

    def test_retrieval_is_scoped_to_current_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            session_dir = temp_path / "session"
            workspace_dir = temp_path / "workspace"
            memory_dir = temp_path / "memory"

            session_dir.mkdir()
            workspace_dir.mkdir()
            memory_dir.mkdir()

            first = Session(
                session_folder=str(session_dir),
                workspace_folder=str(workspace_dir),
                memory_folder=str(memory_dir),
                id="session-1",
            )
            first.add_message({"role": "user", "content": "remember the node service deployment details"})
            first.add_message({"role": "assistant", "content": "deployment is stable"})

            second = Session(
                session_folder=str(session_dir),
                workspace_folder=str(workspace_dir),
                memory_folder=str(memory_dir),
                id="session-2",
            )
            second.add_message({"role": "user", "content": "what was the old deployment status"})

            matches = second.retrieve_past_sessions("deployment", limit=5)
            semantic_matches = second.semantic_retrieve("deployment status", limit=5)

            self.assertFalse(any(item["session_id"] == "session-1" for item in matches))
            self.assertFalse(any(item["session_id"] == "session-1" for item in semantic_matches))
            self.assertTrue(all(item["session_id"] == "session-2" for item in matches))
            self.assertTrue(all(item["session_id"] == "session-2" for item in semantic_matches))

    def test_add_message_is_indexed_into_chroma_immediately(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            session_dir = temp_path / "session"
            workspace_dir = temp_path / "workspace"
            memory_dir = temp_path / "memory"

            session_dir.mkdir()
            workspace_dir.mkdir()
            memory_dir.mkdir()

            session = Session(
                session_folder=str(session_dir),
                workspace_folder=str(workspace_dir),
                memory_folder=str(memory_dir),
                id="session-indexed",
            )
            session.add_message({"role": "user", "content": "deployment is stable"})

            self.assertGreater(session.semantic_index.collection.count(), 0)

    def test_hybrid_retrieval_fuses_semantic_and_lexical_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            session_dir = temp_path / "session"
            workspace_dir = temp_path / "workspace"
            memory_dir = temp_path / "memory"

            session_dir.mkdir()
            workspace_dir.mkdir()
            memory_dir.mkdir()

            first = Session(
                session_folder=str(session_dir),
                workspace_folder=str(workspace_dir),
                memory_folder=str(memory_dir),
                id="session-1",
            )
            first.add_message({"role": "user", "content": "remember the node service deployment details"})
            first.add_message({"role": "assistant", "content": "deployment is stable"})

            second = Session(
                session_folder=str(session_dir),
                workspace_folder=str(workspace_dir),
                memory_folder=str(memory_dir),
                id="session-2",
            )
            second.add_message({"role": "user", "content": "what was the old deployment status"})

            hybrid_matches = second.hybrid_retrieve("deployment status", limit=5)

            self.assertFalse(any(item["session_id"] == "session-1" for item in hybrid_matches))
            self.assertTrue(all(item["session_id"] == "session-2" for item in hybrid_matches))

    def test_hybrid_retrieval_prefers_lower_semantic_distance(self):
        session = Session.__new__(Session)

        def semantic_retrieve(self, query: str, limit: int = 5):
            return [
                {
                    "session_id": "session-1",
                    "message_id": 11,
                    "payload": {"content": "best semantic match"},
                    "score": 0.05,
                },
                {
                    "session_id": "session-1",
                    "message_id": 12,
                    "payload": {"content": "worse semantic match"},
                    "score": 0.9,
                },
            ]

        def retrieve_past_sessions(self, query: str, limit: int = 5):
            return [
                {
                    "session_id": "session-1",
                    "message_id": 13,
                    "payload": {"content": "lexical-only match"},
                }
            ]

        session.semantic_retrieve = MethodType(semantic_retrieve, session)
        session.retrieve_past_sessions = MethodType(retrieve_past_sessions, session)

        hybrid_matches = session.hybrid_retrieve("deployment", limit=3)

        self.assertEqual([item["message_id"] for item in hybrid_matches], [11, 13, 12])
        self.assertLess(hybrid_matches[0]["score"], hybrid_matches[2]["score"])
        self.assertEqual(hybrid_matches[0]["payload"]["content"], "best semantic match")


if __name__ == "__main__":
    unittest.main()
