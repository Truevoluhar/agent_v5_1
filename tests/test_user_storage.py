import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.session import Session
from agent.user_storage import user_storage_paths


class UserStorageTests(unittest.TestCase):
    def test_sessions_and_memory_are_isolated_by_username(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            alice = user_storage_paths(
                "alice",
                session_folder=root / "session",
                memory_folder=root / "memory",
            )
            bob = user_storage_paths(
                "bob",
                session_folder=root / "session",
                memory_folder=root / "memory",
            )

            with patch("agent.session.SemanticMemoryIndex"):
                session = Session(
                    id="shared-id",
                    session_folder=alice.session_folder,
                    workspace_folder=str(root / "workspace"),
                    memory_folder=alice.memory_folder,
                )
                session.add_message({"role": "user", "content": "alice private message"})

            self.assertTrue(Path(alice.session_folder, "session_shared-id.sqlite3").exists())
            self.assertFalse(Path(bob.session_folder, "session_shared-id.sqlite3").exists())
            self.assertNotEqual(alice.memory_folder, bob.memory_folder)

    def test_rejects_usernames_that_could_escape_storage_folder(self):
        with self.assertRaises(ValueError):
            user_storage_paths(
                "../other-user",
                session_folder="session",
                memory_folder="memory",
            )


if __name__ == "__main__":
    unittest.main()