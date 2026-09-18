import tempfile
import unittest
import zipfile
from pathlib import Path
import json

from agent.tools.workspace_fs import workspace_fs_executor


class WorkspaceFsToolTests(unittest.TestCase):
    def test_extract_zip_and_list_tree(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "code.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("demo/main.py", "print('hi')\n")
                zf.writestr("demo/README.md", "# Demo\n")

            extracted = workspace_fs_executor(
                workspace=root,
                action="extract_zip",
                zip_path="code.zip",
                destination="unzipped",
                overwrite=False,
            )
            self.assertTrue(extracted.ok)
            self.assertTrue((root / "unzipped" / "demo" / "main.py").exists())

            tree = workspace_fs_executor(
                workspace=root,
                action="list_tree",
                root="unzipped",
                pattern="**/*",
                max_entries=20,
            )
            self.assertTrue(tree.ok)
            self.assertIn("unzipped/demo/main.py", tree.output or "")

    def test_read_and_write_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write = workspace_fs_executor(
                workspace=root,
                action="write_text",
                path="docs/a.txt",
                content="hello world",
                append=False,
            )
            self.assertTrue(write.ok)

            read = workspace_fs_executor(
                workspace=root,
                action="read_text",
                path="docs/a.txt",
                max_chars=5,
                offset=0,
            )
            self.assertTrue(read.ok)
            self.assertEqual(read.output, "hello")
            self.assertEqual(read.metadata["next_offset"], 5)

    def test_read_text_clamps_oversized_max_chars(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample = root / "docs.txt"
            sample.write_text("abc", encoding="utf-8")

            read = workspace_fs_executor(
                workspace=root,
                action="read_text",
                path="docs.txt",
                max_chars=50000,
                offset=0,
            )
            self.assertTrue(read.ok)
            self.assertEqual(read.output, "abc")
            self.assertEqual(read.metadata["requested_max_chars"], 50000)
            self.assertEqual(read.metadata["applied_max_chars"], 12000)

    def test_snapshot_summarizes_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "doc.txt").write_text("hello\n", encoding="utf-8")
            (root / "blob.bin").write_bytes(b"\x00\x01")
            with zipfile.ZipFile(root / "bundle.zip", "w") as zf:
                zf.writestr("nested.txt", "data")

            snapshot = workspace_fs_executor(
                workspace=root,
                action="snapshot",
                root=".",
                max_entries=10,
            )
            self.assertTrue(snapshot.ok)
            data = json.loads(snapshot.output or "{}")
            self.assertIn("bundle.zip", data["archives"])
            self.assertIn("src", data["candidate_source_dirs"])
            self.assertGreaterEqual(data["text_like_files"], 2)
            self.assertGreaterEqual(data["binary_like_files"], 1)


if __name__ == "__main__":
    unittest.main()
