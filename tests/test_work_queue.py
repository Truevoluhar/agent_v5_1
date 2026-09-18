import json
import tempfile
import unittest
from pathlib import Path

from agent.tools.tools_registry import execute_registered_tool
from agent.work_queue import TaskBoard


class TaskBoardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.board = TaskBoard(self.root, "session")

    def test_objective_and_task_creation_survive_reopening(self):
        self.assertEqual(self.board.objective("Ship the feature"), "Ship the feature")
        created = self.board.add_tasks(
            [
                {
                    "task_key": "TASK-ANALYZE",
                    "title": "Analyze the repo",
                    "description": "Inspect the current implementation.",
                    "task_type": "analysis",
                    "priority": 10,
                }
            ]
        )
        reopened = TaskBoard(self.root, "session")
        self.assertEqual(reopened.total_tasks(), 1)
        self.assertEqual(reopened.next_ready()["task_key"], "TASK-ANALYZE")
        self.assertEqual(created[0]["task_key"], "TASK-ANALYZE")

    def test_dependencies_control_when_tasks_become_ready(self):
        self.board.add_tasks(
            [
                {
                    "task_key": "TASK-1",
                    "title": "Inspect",
                    "description": "Inspect",
                    "task_type": "analysis",
                    "priority": 10,
                },
                {
                    "task_key": "TASK-2",
                    "title": "Implement",
                    "description": "Implement",
                    "task_type": "implementation",
                    "priority": 20,
                    "depends_on_keys": ["TASK-1"],
                },
            ]
        )
        first = self.board.next_ready()
        self.assertEqual(first["task_key"], "TASK-1")
        self.board.begin_task(first["id"], "PLANNER", "Inspect")
        self.board.submit(first["id"], summary="done", evidence="checked repo", artifacts=[])
        self.board.validate(first["id"], accepted=True, validation_notes="Looks good")
        second = self.board.next_ready()
        self.assertEqual(second["task_key"], "TASK-2")

    def test_submit_validate_and_completion_report(self):
        artifact = self.root / "notes.md"
        artifact.write_text("verified", encoding="utf-8")
        self.board.add_tasks(
            [
                {
                    "task_key": "TASK-VERIFY",
                    "title": "Verify",
                    "description": "Verify",
                    "task_type": "verification",
                    "priority": 5,
                }
            ]
        )
        task = self.board.next_ready()
        self.board.begin_task(task["id"], "PROGRAMMER", "Verify it")
        self.board.submit(
            task["id"],
            summary="verified",
            evidence="Read the file and confirmed it exists",
            artifacts=["notes.md"],
        )
        self.board.validate(task["id"], accepted=True, validation_notes="Accepted")
        report = self.board.completion_report()
        self.assertEqual(report["validated_tasks"], 1)
        self.assertEqual(report["artifact_paths"], ["notes.md"])
        saved = json.loads((self.root / report["full_report"]).read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["task_key"], "TASK-VERIFY")

    def test_verify_invalidates_changed_artifacts(self):
        artifact = self.root / "result.txt"
        artifact.write_text("v1", encoding="utf-8")
        self.board.add_tasks(
            [
                {
                    "task_key": "TASK-RESULT",
                    "title": "Result",
                    "description": "Generate result",
                    "task_type": "implementation",
                    "priority": 1,
                }
            ]
        )
        task = self.board.next_ready()
        self.board.begin_task(task["id"], "PROGRAMMER", "Do the work")
        self.board.submit(
            task["id"],
            summary="done",
            evidence="Generated the file",
            artifacts=["result.txt"],
        )
        self.board.validate(task["id"], accepted=True, validation_notes="Accepted")
        artifact.write_text("v2", encoding="utf-8")
        state = self.board.verify()
        self.assertEqual(state["invalidated"], [])
        self.assertEqual(self.board.get_task(task_id=task["id"])["status"], "validated")

    def test_verify_still_hashes_internal_agent_artifacts(self):
        artifact_dir = self.root / ".agent"
        artifact_dir.mkdir(exist_ok=True)
        artifact = artifact_dir / "report.json"
        artifact.write_text('{"ok": true}', encoding="utf-8")
        self.board.add_tasks(
            [
                {
                    "task_key": "TASK-REPORT",
                    "title": "Create report",
                    "description": "Save an internal report",
                    "task_type": "verification",
                    "priority": 1,
                }
            ]
        )
        task = self.board.next_ready()
        self.board.begin_task(task["id"], "PROGRAMMER", "Create internal report")
        self.board.submit(
            task["id"],
            summary="done",
            evidence="Generated report",
            artifacts=[".agent/report.json"],
        )
        self.board.validate(task["id"], accepted=True, validation_notes="Accepted")
        artifact.write_text('{"ok": false}', encoding="utf-8")
        state = self.board.verify()
        self.assertEqual(state["invalidated"], [task["id"]])
        self.assertEqual(self.board.get_task(task_id=task["id"])["status"], "blocked")

    def test_submit_is_idempotent_after_first_report(self):
        artifact = self.root / "out.txt"
        artifact.write_text("done", encoding="utf-8")
        self.board.add_tasks(
            [
                {
                    "task_key": "TASK-IDEMPOTENT",
                    "title": "Report twice",
                    "description": "Worker may resubmit",
                    "task_type": "implementation",
                    "priority": 1,
                }
            ]
        )
        task = self.board.next_ready()
        self.board.begin_task(task["id"], "PROGRAMMER", "Submit twice")
        self.board.submit(task["id"], summary="first", evidence="first evidence", artifacts=["out.txt"])
        self.board.submit(task["id"], summary="second", evidence="second evidence", artifacts=["out.txt"])
        saved = self.board.get_task(task_id=task["id"])
        self.assertEqual(saved["status"], "reported")
        self.assertEqual(saved["result_summary"], "second")

    def test_shell_requires_a_running_task(self):
        refused = execute_registered_tool(
            workspace=str(self.root),
            tool_name="run_shell",
            tool_input={"command": "printf blocked > blocked.txt", "cwd": ".", "timeout": 5, "background": False},
            scope="session",
        )
        self.assertFalse(refused["ok"])
        self.assertFalse((self.root / "blocked.txt").exists())

        self.board.add_tasks(
            [
                {
                    "task_key": "TASK-SHELL",
                    "title": "Shell",
                    "description": "Create a file",
                    "task_type": "implementation",
                    "priority": 1,
                }
            ]
        )
        task = self.board.next_ready()
        self.board.begin_task(task["id"], "PROGRAMMER", "Create the file")
        result = execute_registered_tool(
            workspace=str(self.root),
            tool_name="run_shell",
            tool_input={"command": "printf recorded > evidence.txt", "cwd": ".", "timeout": 5, "background": False},
            scope="session",
        )
        self.assertTrue(result["ok"])
        self.assertEqual((self.root / "evidence.txt").read_text(encoding="utf-8"), "recorded")

    def test_task_board_tool_exposes_current_and_submit(self):
        artifact = self.root / "out.txt"
        artifact.write_text("done", encoding="utf-8")
        self.board.add_tasks(
            [
                {
                    "task_key": "TASK-TOOL",
                    "title": "Tool",
                    "description": "Use the tool API",
                    "task_type": "implementation",
                    "priority": 1,
                }
            ]
        )
        task = self.board.next_ready()
        self.board.begin_task(task["id"], "PROGRAMMER", "Use task_board")
        current = execute_registered_tool(
            workspace=str(self.root),
            tool_name="task_board",
            tool_input={"action": "current"},
            scope="session",
        )
        self.assertTrue(current["ok"])
        self.assertIn("TASK-TOOL", current["output"])

        submitted = execute_registered_tool(
            workspace=str(self.root),
            tool_name="task_board",
            tool_input={
                "action": "submit",
                "task_id": task["id"],
                "summary": "done",
                "evidence": "Created out.txt",
                "artifacts": ["out.txt"],
            },
            scope="session",
        )
        self.assertTrue(submitted["ok"])
        self.assertEqual(self.board.get_task(task_id=task["id"])["status"], "reported")

    def test_task_board_current_falls_back_to_requested_task(self):
        self.board.add_tasks(
            [
                {
                    "task_key": "TASK-FALLBACK",
                    "title": "Fallback",
                    "description": "Inspect specific task",
                    "task_type": "analysis",
                    "priority": 1,
                }
            ]
        )
        task = self.board.get_task(task_key="TASK-FALLBACK")
        current = execute_registered_tool(
            workspace=str(self.root),
            tool_name="task_board",
            tool_input={
                "action": "current",
                "task_id": task["id"],
                "task_key": "TASK-FALLBACK",
            },
            scope="session",
        )
        self.assertTrue(current["ok"])
        self.assertIn("TASK-FALLBACK", current["output"])

    def test_inventory_skips_binary_files_by_default(self):
        source_dir = self.root / "mixed"
        source_dir.mkdir()
        (source_dir / "a.py").write_text("print('ok')\n", encoding="utf-8")
        (source_dir / "b.bin").write_bytes(b"\x00\x01\x02\x03")

        result = self.board.inventory(
            root="mixed",
            pattern="**/*",
            task_type="analysis",
            title_prefix="Inspect",
            description_template="Inspect {source_path}",
            acceptance_criteria=["Inspected"],
            suggested_agent="PROGRAMMER",
            priority=5,
        )

        self.assertEqual(result["discovered"], 1)
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["skipped_binary"], 1)
        task = self.board.next_ready()
        self.assertEqual(task["source_path"], "mixed/a.py")

    def test_task_memory_remember_and_recall(self):
        self.board.add_tasks(
            [
                {
                    "task_key": "TASK-MEM",
                    "title": "Remember work",
                    "description": "Store durable findings",
                    "task_type": "analysis",
                    "priority": 1,
                }
            ]
        )
        task = self.board.next_ready()
        self.board.begin_task(task["id"], "PLANNER", "Inspect and remember")
        saved = self.board.remember(
            task["id"],
            content="Discovered that module loader expects relative imports only.",
            note_type="finding",
            agent_name="PLANNER",
        )
        recalled = self.board.recall(query="relative imports", task_id=task["id"], limit=5)

        self.assertEqual(saved["task_key"], "TASK-MEM")
        self.assertTrue(recalled["semantic_matches"] or recalled["lexical_matches"])
        all_matches = recalled["semantic_matches"] + recalled["lexical_matches"]
        self.assertTrue(any("relative imports" in match["content"].lower() for match in all_matches))

    def test_inventory_and_read_source_support_large_file_sets(self):
        project = self.root / "project"
        project.mkdir()
        for idx in range(3):
            (project / f"file{idx}.py").write_text(f"print({idx})\n", encoding="utf-8")
        nested = project / "nested"
        nested.mkdir()
        (nested / "deep.py").write_text("print('deep')\n", encoding="utf-8")
        (self.root / "TEMPLATE_README.md").write_text("# Template\n", encoding="utf-8")

        seeded = execute_registered_tool(
            workspace=str(self.root),
            tool_name="task_board",
            tool_input={
                "action": "inventory",
                "task_id": 0,
                "task_key": None,
                "summary": "Analyze {source_path} and create a README that follows TEMPLATE_README.md.",
                "evidence": "",
                "text": "",
                "artifacts": [],
                "limit": 10,
                "root": "project",
                "pattern": "*.py",
                "task_type": "analysis",
                "title_prefix": "Analyze",
                "suggested_agent": "PROGRAMMER",
                "priority": 20,
                "acceptance_criteria": ["README created"],
                "max_chars": 4000,
                "parent_task_id": None,
            },
            scope="session",
        )
        self.assertTrue(seeded["ok"])
        self.assertEqual(self.board.total_tasks(), 4)
        planned = self.board.get_task(task_key="FILE-PROJECT-FILE0_PY")
        self.assertEqual(planned["task_metadata"]["entity_name"], "file0")
        self.assertEqual(planned["task_metadata"]["group_name"], "file0")
        self.assertEqual(planned["task_metadata"]["target_dir"], "file0")
        self.assertEqual(planned["task_metadata"]["target_path"], "file0/README.md")
        self.assertEqual(planned["task_metadata"]["reference_paths"], ["TEMPLATE_README.md"])
        self.assertIn("file0/README.md", planned["description"])
        nested_task = self.board.get_task(task_key="FILE-PROJECT-NESTED-DEEP_PY")
        self.assertEqual(nested_task["source_path"], "project/nested/deep.py")

        task = self.board.next_ready()
        self.board.begin_task(task["id"], "PROGRAMMER", "Analyze the file")
        chunk = execute_registered_tool(
            workspace=str(self.root),
            tool_name="task_board",
            tool_input={
                "action": "read_source",
                "task_id": task["id"],
                "task_key": None,
                "summary": "",
                "evidence": "",
                "text": "",
                "artifacts": [],
                "limit": 10,
                "root": ".",
                "pattern": "**/*",
                "task_type": "implementation",
                "title_prefix": "",
                "suggested_agent": None,
                "priority": 50,
                "acceptance_criteria": [],
                "max_chars": 4000,
                "parent_task_id": None,
            },
            scope="session",
        )
        self.assertTrue(chunk["ok"])
        self.assertIn("print", chunk["output"])

    def test_read_source_supports_non_utf8_text_files(self):
        project = self.root / "project"
        project.mkdir()
        (project / "legacy.txt").write_bytes(b"Line one\nBullet\x8a line\n")
        self.board.add_tasks(
            [
                {
                    "task_key": "FILE-LEGACY",
                    "title": "Analyze legacy.txt",
                    "description": "Analyze legacy.txt",
                    "task_type": "analysis",
                    "priority": 1,
                    "source_path": "project/legacy.txt",
                }
            ]
        )
        task = self.board.next_ready()
        self.board.begin_task(task["id"], "PROGRAMMER", "Read it")
        chunk = self.board.read_source(task["id"], max_chars=4000)
        self.assertEqual(chunk["encoding"], "cp1252")
        self.assertIn("Line one", chunk["content"])

    def test_add_tasks_derives_project_output_fields_for_file_tasks(self):
        source_dir = self.root / "source_code"
        source_dir.mkdir()
        (self.root / "TEMPLATE_README.md").write_text("# Template\n", encoding="utf-8")
        (source_dir / "AD576__AD5761S.txt").write_text("PROC OPTIONS(MAIN);", encoding="utf-8")
        created = self.board.add_tasks(
            [
                {
                    "task_key": "FILE-AD576",
                    "title": "Generate README",
                    "description": "Analyze the source",
                    "task_type": "documentation",
                    "priority": 1,
                    "source_path": "source_code/AD576__AD5761S.txt",
                }
            ]
        )
        self.assertEqual(created[0]["task_metadata"]["entity_name"], "AD576_AD5761S")
        self.assertEqual(created[0]["task_metadata"]["group_name"], "AD576")
        self.assertEqual(created[0]["task_metadata"]["target_dir"], "AD576/AD576_AD5761S")
        self.assertEqual(created[0]["task_metadata"]["target_path"], "AD576/AD576_AD5761S/README.md")
        self.assertEqual(created[0]["task_metadata"]["reference_paths"], ["TEMPLATE_README.md"])

    def test_add_tasks_normalizes_dependency_key_casing(self):
        self.board.add_tasks(
            [
                {
                    "task_key": "EXTRACT_ZIP",
                    "title": "Extract zip",
                    "description": "Extract files",
                    "task_type": "implementation",
                    "priority": 1,
                },
                {
                    "task_key": "INSPECT_WORKSPACE",
                    "title": "Inspect workspace",
                    "description": "Inspect files",
                    "task_type": "analysis",
                    "priority": 2,
                    "depends_on_keys": ["extract_zip"],
                },
            ]
        )
        extract = self.board.get_task(task_key="EXTRACT_ZIP")
        self.board.begin_task(extract["id"], "PROGRAMMER", "Extract")
        self.board.submit(extract["id"], summary="done", evidence="done", artifacts=[])
        self.board.validate(extract["id"], accepted=True, validation_notes="ok")
        inspect_task = self.board.get_task(task_key="INSPECT_WORKSPACE")
        self.assertEqual(inspect_task["depends_on_keys"], ["EXTRACT_ZIP"])
        self.assertEqual(inspect_task["status"], "ready")


if __name__ == "__main__":
    unittest.main()
