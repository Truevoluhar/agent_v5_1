import json
import tempfile
import unittest
from pathlib import Path

from agent.session import Session


class SessionSqliteTests(unittest.TestCase):

    def test_session_persists_and_reloads_messages_with_sqlite(self):
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

            session.add_message({"role": "user", "content": "hello"})
            session.add_message({"role": "assistant", "content": "world"})

            reloaded = Session(
                session_folder=str(session_dir),
                workspace_folder=str(workspace_dir),
                memory_folder=str(memory_dir),
                id=session.id,
            )

            messages = reloaded.get_messages_for_agent()

            self.assertEqual([msg["role"] for msg in messages], ["user", "assistant"])
            self.assertEqual(messages[0]["content"], "hello")
            self.assertEqual(messages[1]["content"], "world")

            db_file = session_dir / f"session_{session.id}.sqlite3"
            self.assertTrue(db_file.exists())

    def test_session_migrates_legacy_jsonl_to_sqlite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            session_dir = temp_path / "session"
            workspace_dir = temp_path / "workspace"
            memory_dir = temp_path / "memory"

            session_dir.mkdir()
            workspace_dir.mkdir()
            memory_dir.mkdir()

            legacy_session_id = "legacy-session"
            legacy_file = session_dir / f"session_{legacy_session_id}.jsonl"
            with legacy_file.open("w", encoding="utf-8") as f:
                f.write(json.dumps({"role": "user", "content": "legacy"}) + "\n")
                f.write(json.dumps({"role": "assistant", "content": "migrated"}) + "\n")

            session = Session(
                session_folder=str(session_dir),
                workspace_folder=str(workspace_dir),
                memory_folder=str(memory_dir),
                id=legacy_session_id,
            )

            messages = session.get_messages_for_agent()
            self.assertEqual([msg["content"] for msg in messages], ["legacy", "migrated"])


if __name__ == "__main__":
    unittest.main()
