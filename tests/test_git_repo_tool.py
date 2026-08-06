import subprocess
import tempfile
import unittest
from pathlib import Path

from agent.tools.git_repo import git_repo_browser_executor


class GitRepoBrowserToolTests(unittest.TestCase):

    def _create_local_git_repo(self, base_dir: Path) -> Path:
        repo = base_dir / "source_repo"
        repo.mkdir(parents=True, exist_ok=True)

        subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo), check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(repo), check=True, capture_output=True, text=True)

        (repo / "README.md").write_text("# Demo\n\nhello\n", encoding="utf-8")
        (repo / "src").mkdir(parents=True, exist_ok=True)
        (repo / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (repo / ".hidden.txt").write_text("secret\n", encoding="utf-8")

        subprocess.run(["git", "add", "."], cwd=str(repo), check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo), check=True, capture_output=True, text=True)

        return repo

    def test_clone_list_and_read(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            source_repo = self._create_local_git_repo(workspace)

            clone_result = git_repo_browser_executor(
                workspace=workspace,
                action="clone",
                repo_url=str(source_repo),
                repo_name="demo_clone",
                repo_dir=None,
                file_path=None,
                clone_root="clones",
                branch=None,
                depth=1,
                recursive=True,
                include_hidden=False,
                max_entries=200,
                max_chars=4000,
                timeout=60,
            )
            self.assertTrue(clone_result.ok, msg=clone_result.error)
            repo_dir = clone_result.metadata.get("repo_dir")
            self.assertIsNotNone(repo_dir)

            list_result = git_repo_browser_executor(
                workspace=workspace,
                action="list_files",
                repo_url=None,
                repo_name=None,
                repo_dir="clones/demo_clone",
                file_path=None,
                clone_root="clones",
                branch=None,
                depth=1,
                recursive=True,
                include_hidden=False,
                max_entries=200,
                max_chars=4000,
                timeout=60,
            )
            self.assertTrue(list_result.ok, msg=list_result.error)
            output = list_result.output or ""
            self.assertIn("README.md", output)
            self.assertIn("src/main.py", output)
            self.assertNotIn(".hidden.txt", output)

            read_result = git_repo_browser_executor(
                workspace=workspace,
                action="read_file",
                repo_url=None,
                repo_name=None,
                repo_dir="clones/demo_clone",
                file_path="README.md",
                clone_root="clones",
                branch=None,
                depth=1,
                recursive=True,
                include_hidden=False,
                max_entries=200,
                max_chars=4000,
                timeout=60,
            )
            self.assertTrue(read_result.ok, msg=read_result.error)
            self.assertIn("# Demo", read_result.output or "")

    def test_read_prevents_path_escape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            source_repo = self._create_local_git_repo(workspace)

            clone_result = git_repo_browser_executor(
                workspace=workspace,
                action="clone",
                repo_url=str(source_repo),
                repo_name="safe_repo",
                repo_dir=None,
                file_path=None,
                clone_root="clones",
                branch=None,
                depth=1,
                recursive=True,
                include_hidden=False,
                max_entries=200,
                max_chars=4000,
                timeout=60,
            )
            self.assertTrue(clone_result.ok, msg=clone_result.error)

            read_result = git_repo_browser_executor(
                workspace=workspace,
                action="read_file",
                repo_url=None,
                repo_name=None,
                repo_dir="clones/safe_repo",
                file_path="../../outside.txt",
                clone_root="clones",
                branch=None,
                depth=1,
                recursive=True,
                include_hidden=False,
                max_entries=200,
                max_chars=4000,
                timeout=60,
            )
            self.assertFalse(read_result.ok)
            self.assertIn("must stay inside repo_dir", read_result.error or "")


if __name__ == "__main__":
    unittest.main()
