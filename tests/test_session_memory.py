import tempfile
import unittest
from pathlib import Path

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

    def test_retrieval_across_past_sessions(self):
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

            self.assertTrue(any(item["session_id"] == "session-1" for item in matches))
            self.assertTrue(any(item["session_id"] == "session-1" for item in semantic_matches))

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

            self.assertTrue(any(item["session_id"] == "session-1" for item in hybrid_matches))


if __name__ == "__main__":
    unittest.main()
