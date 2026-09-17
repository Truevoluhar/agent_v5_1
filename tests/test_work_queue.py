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

    def test_inventory_and_read_source_support_large_file_sets(self):
        project = self.root / "project"
        project.mkdir()
        for idx in range(3):
            (project / f"file{idx}.py").write_text(f"print({idx})\n", encoding="utf-8")

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
        self.assertEqual(self.board.total_tasks(), 3)

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


if __name__ == "__main__":
    unittest.main()
