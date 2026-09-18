import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError

from agent.execution import BudgetExhausted
from agent.orchestrator_agent import create_orchestrator_response
from agent.runner import (
    AgentRunner,
    _auto_submit_completed_artifact_task,
    _auto_submit_seed_task,
    _cleanup_redundant_collection_tasks,
    _requires_bootstrap_before_dispatch,
)
from agent.tools.tools_registry import execute_registered_tool
from agent.work_queue import TaskBoard


class SessionStub:
    id = "test"

    def __init__(self):
        self.messages = [{"role": "user", "content": "Do all tasks"}]

    def add_message(self, message):
        self.messages.append(message)

    def get_bounded_context(self, **kwargs):
        return list(self.messages)

    def format_retrieval_context(self, **kwargs):
        return ""


class RunnerScaleTests(unittest.TestCase):
    def test_session_title_is_local_bounded_and_readable(self):
        title = AgentRunner._generate_session_name(
            "# Inspect **one thousand** files and create `README.md` for each"
        )
        self.assertEqual(title, "Inspect one thousand files and create README.md for")
        self.assertLessEqual(len(title.split()), 8)

    def test_empty_prompt_uses_default_session_title(self):
        self.assertEqual(AgentRunner._generate_session_name("  \n"), "New chat")

    def run_loop(self, workspace, orchestrator, agents=None, steps=3):
        emitter = SimpleNamespace(emit=lambda *args: None)
        runner = AgentRunner.__new__(AgentRunner)
        return runner._run_loop(
            session=SessionStub(),
            config={"max_steps": steps, "max_worker_iterations": 5},
            agents=agents or [],
            orchestrator_agent=orchestrator,
            response_agent=None,
            agent_workspace=workspace,
            orchestrator_context_budget=10000,
            delegated_context_budget=10000,
            response_context_budget=10000,
            response_schema_source=None,
            emitter=emitter,
            wait_for_input=lambda question: "",
            is_cancelled=lambda: False,
        )

    def test_finish_is_rejected_when_board_is_incomplete(self):
        with tempfile.TemporaryDirectory() as workspace:
            board = TaskBoard(workspace, "test")
            artifact_dir = Path(workspace) / ".agent"
            artifact_dir.mkdir(exist_ok=True)
            artifact = artifact_dir / "report.json"
            artifact.write_text('{"ok": true}', encoding="utf-8")
            board.add_tasks(
                [
                    {
                        "task_key": "TASK-1",
                        "title": "Unfinished",
                        "description": "Do it",
                        "task_type": "implementation",
                        "priority": 1,
                    }
                ]
            )
            orchestrator = SimpleNamespace(
                plan_tasks=lambda messages: SimpleNamespace(summary="unused", tasks=[]),
                decide_next_action=lambda messages: SimpleNamespace(action="finish", description="done", task_key=None, agent_name=None),
                review_task=lambda messages: SimpleNamespace(outcome="accept", validation_notes="ok", new_tasks=[]),
            )
            with self.assertRaises(BudgetExhausted):
                self.run_loop(workspace, orchestrator, steps=1)

    def test_worker_budget_yields_and_next_batch_can_finish(self):
        with tempfile.TemporaryDirectory() as workspace:
            board = TaskBoard(workspace, "test")
            board.add_tasks(
                [
                    {
                        "task_key": "TASK-1",
                        "title": "Work",
                        "description": "Continue",
                        "task_type": "implementation",
                        "priority": 1,
                    }
                ]
            )
            calls = []

            def chat(*args, **kwargs):
                calls.append(1)
                task = board.get_task(task_key="TASK-1")
                if len(calls) == 1:
                    raise BudgetExhausted()
                board.submit(task["id"], summary="done", evidence="validated", artifacts=[])

            worker = SimpleNamespace(name="WORKER", chat=chat)
            decisions = [
                SimpleNamespace(action="delegate_to_agent", agent_name="WORKER", task_key="TASK-1", description="Do the work"),
                SimpleNamespace(action="delegate_to_agent", agent_name="WORKER", task_key="TASK-1", description="Resume the work"),
                SimpleNamespace(action="finish", description="done", task_key=None, agent_name=None),
            ]
            orchestrator = SimpleNamespace(
                plan_tasks=lambda messages: SimpleNamespace(summary="unused", tasks=[]),
                decide_next_action=lambda messages: decisions.pop(0),
                review_task=lambda messages: (
                    SimpleNamespace(outcome="rework", validation_notes="resume it", new_tasks=[])
                    if '"status": "blocked"' in messages[-1]["content"]
                    else SimpleNamespace(outcome="accept", validation_notes="accepted", new_tasks=[])
                ),
            )
            self.assertIsNone(self.run_loop(workspace, orchestrator, [worker], steps=5))
            self.assertEqual(len(calls), 2)
            self.assertEqual(board.summary()["remaining"], 0)

    def test_step_budget_auto_scales_to_cover_delegate_and_review(self):
        with tempfile.TemporaryDirectory() as workspace:
            board = TaskBoard(workspace, "test")
            board.add_tasks(
                [
                    {
                        "task_key": "TASK-1",
                        "title": "Write README",
                        "description": "Create the README file",
                        "task_type": "implementation",
                        "priority": 1,
                    }
                ]
            )

            def chat(*args, **kwargs):
                task = board.get_task(task_key="TASK-1")
                board.submit(task["id"], summary="done", evidence="created readme", artifacts=[])

            worker = SimpleNamespace(name="WORKER", chat=chat)
            decisions = [
                SimpleNamespace(action="delegate_to_agent", agent_name="WORKER", task_key="TASK-1", description="Write the README"),
                SimpleNamespace(action="finish", description="done", task_key=None, agent_name=None),
            ]
            orchestrator = SimpleNamespace(
                plan_tasks=lambda messages: SimpleNamespace(summary="unused", tasks=[]),
                decide_next_action=lambda messages: decisions.pop(0),
                review_task=lambda messages: SimpleNamespace(outcome="accept", validation_notes="accepted", new_tasks=[]),
            )
            self.assertIsNone(self.run_loop(workspace, orchestrator, [worker], steps=1))
            self.assertEqual(board.summary()["remaining"], 0)

    def test_delegation_passes_current_task_to_worker(self):
        with tempfile.TemporaryDirectory() as workspace:
            captured = []
            board = TaskBoard(workspace, "test")
            board.add_tasks(
                [
                    {
                        "task_key": "TASK-IMPL",
                        "title": "Implement",
                        "description": "Implement the change",
                        "task_type": "implementation",
                        "priority": 1,
                    }
                ]
            )

            def chat(messages, *args, **kwargs):
                captured.extend(messages)
                task = board.get_task(task_key="TASK-IMPL")
                board.submit(task["id"], summary="implemented", evidence="checked", artifacts=[])

            worker = SimpleNamespace(name="WORKER", chat=chat)
            orchestrator = SimpleNamespace(
                plan_tasks=lambda messages: SimpleNamespace(summary="unused", tasks=[]),
                decide_next_action=lambda messages: SimpleNamespace(
                    action="delegate_to_agent",
                    agent_name="WORKER",
                    task_key="TASK-IMPL",
                    description="Implement the change",
                ),
                review_task=lambda messages: SimpleNamespace(outcome="accept", validation_notes="accepted", new_tasks=[]),
            )
            self.assertIsNone(self.run_loop(workspace, orchestrator, [worker], steps=3))
            worker_prompt = captured[-1]["content"]
            self.assertIn("Implement the change", worker_prompt)
            self.assertIn("task_board(action='submit')", worker_prompt)

    def test_delegation_instructions_are_hardened_when_orchestrator_is_vague(self):
        with tempfile.TemporaryDirectory() as workspace:
            board = TaskBoard(workspace, "test")
            source_dir = Path(workspace) / "extracted_documents"
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "ADGZ__ADGZ.txt").write_text("sample source", encoding="utf-8")
            board.add_tasks(
                [
                    {
                        "task_key": "TASK-README",
                        "title": "README for extracted_documents/ADGZ__ADGZ.txt",
                        "description": "Read and analyze a source file, then create a comprehensive README.md following the template format.",
                        "task_type": "implementation",
                        "priority": 1,
                        "acceptance_criteria": [
                            "README.md follows TEMPLATE_README.md format exactly",
                            "README.md is placed in a folder named after the project",
                        ],
                        "source_path": "extracted_documents/ADGZ__ADGZ.txt",
                        "task_metadata": {
                            "entity_name": "ADGZ_ADGZ",
                            "group_name": "ADGZ",
                            "target_dir": "ADGZ_ADGZ",
                            "target_path": "ADGZ_ADGZ/README.md",
                            "reference_paths": ["TEMPLATE_README.md"],
                        },
                    }
                ]
            )
            seen = {}

            def chat(*args, **kwargs):
                current = board.active_task()
                seen["instructions"] = current["delegation_instructions"]
                board.read_source(current["id"], max_chars=1000)
                board.submit(current["id"], summary="done", evidence="created readme", artifacts=[])

            worker = SimpleNamespace(name="WORKER", chat=chat)
            orchestrator = SimpleNamespace(
                plan_tasks=lambda messages: SimpleNamespace(summary="unused", tasks=[]),
                decide_next_action=lambda messages: SimpleNamespace(
                    action="delegate_to_agent",
                    agent_name="WORKER",
                    task_key="TASK-README",
                    description="Delegate next task",
                ),
                review_task=lambda messages: SimpleNamespace(outcome="accept", validation_notes="accepted", new_tasks=[]),
            )
            self.assertIsNone(self.run_loop(workspace, orchestrator, [worker], steps=3))
            self.assertIn("TASK-README", seen["instructions"])
            self.assertIn("extracted_documents/ADGZ__ADGZ.txt", seen["instructions"])
            self.assertIn("README.md follows TEMPLATE_README.md format exactly", seen["instructions"])
            self.assertIn("ADGZ_ADGZ/README.md", seen["instructions"])
            self.assertNotEqual(seen["instructions"], "Delegate next task")

    def test_collection_wide_task_waits_for_seed_backlog(self):
        with tempfile.TemporaryDirectory() as workspace:
            board = TaskBoard(workspace, "test")
            board.add_tasks(
                [
                    {
                        "task_key": "SEED_README_TASKS",
                        "title": "Create inventory and seed per-file README tasks",
                        "description": "Inventory files and create durable per-file tasks.",
                        "task_type": "analysis",
                        "priority": 1,
                    },
                    {
                        "task_key": "GENERATE_READMES",
                        "title": "Generate comprehensive README.md for each extracted file",
                        "description": "Read all files and create a README for each file.",
                        "task_type": "implementation",
                        "priority": 1,
                    },
                ]
            )
            aggregate = board.get_task(task_key="GENERATE_READMES")
            self.assertTrue(_requires_bootstrap_before_dispatch(board, aggregate))

    def test_runtime_scaffold_does_not_duplicate_extract_tasks(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            with zipfile.ZipFile(root / "source_bundle.zip", "w") as zf:
                zf.writestr("demo.py", "print('ok')\n")
            board = TaskBoard(workspace, "test")
            runner = AgentRunner.__new__(AgentRunner)
            emitter = SimpleNamespace(emit=lambda *args, **kwargs: None)
            worker = SimpleNamespace(name="PROGRAMMER")

            runner._ensure_runtime_scaffold(
                board=board,
                objective="Extract the zip and create a README for each file.",
                agents=[worker],
                agent_workspace=workspace,
                emitter=emitter,
            )
            runner._ensure_runtime_scaffold(
                board=board,
                objective="Extract the zip and create a README for each file.",
                agents=[worker],
                agent_workspace=workspace,
                emitter=emitter,
            )

            tasks = board.list_tasks(limit=50)
            extract_keys = [task["task_key"] for task in tasks if task["task_key"].startswith("EXTRACT-SOURCE_BUNDLE")]
            self.assertEqual(extract_keys, ["EXTRACT-SOURCE_BUNDLE"])

    def test_runtime_scaffold_still_adds_seed_task_when_llm_added_bad_inventory_task(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            extracted = root / "extracted" / "source_bundle"
            extracted.mkdir(parents=True)
            (extracted / "demo.py").write_text("print('ok')\n", encoding="utf-8")
            board = TaskBoard(workspace, "test")
            board.add_tasks(
                [
                    {
                        "task_key": "TASK-INVENTORY-BAD",
                        "title": "Inventory extracted files",
                        "description": "Inventory files from source_bundle_extracted.",
                        "task_type": "analysis",
                        "priority": 20,
                    }
                ]
            )
            runner = AgentRunner.__new__(AgentRunner)
            emitter = SimpleNamespace(emit=lambda *args, **kwargs: None)
            worker = SimpleNamespace(name="PROGRAMMER")

            runner._ensure_runtime_scaffold(
                board=board,
                objective="Extract the zip and create a README for each file.",
                agents=[worker],
                agent_workspace=workspace,
                emitter=emitter,
            )

            seed_keys = [task["task_key"] for task in board.list_tasks(limit=50) if task["task_key"].startswith("SEED-")]
            self.assertIn("SEED-EXTRACTED", seed_keys)

    def test_auto_submit_completed_artifact_task_recovers_worker_output(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "TEMPLATE_README.md").write_text("# Template\n", encoding="utf-8")
            source_dir = root / "src"
            source_dir.mkdir()
            (source_dir / "PROJ00__MODULE_00.py").write_text("print('ok')\n", encoding="utf-8")
            board = TaskBoard(workspace, "test")
            created = board.add_tasks(
                [
                    {
                        "task_key": "FILE-SRC-PROJ00__MODULE_00_PY",
                        "title": "Generate README",
                        "description": "Create README for file",
                        "task_type": "documentation",
                        "priority": 1,
                        "source_path": "src/PROJ00__MODULE_00.py",
                    }
                ]
            )
            task = board.next_ready()
            board.begin_task(task["id"], "PROGRAMMER", "Create the README")
            board.read_source(task["id"], max_chars=4000)
            target_path = created[0]["task_metadata"]["target_path"]
            (root / target_path).parent.mkdir(parents=True, exist_ok=True)
            (root / target_path).write_text("# README\n", encoding="utf-8")

            updated = _auto_submit_completed_artifact_task(
                board,
                board.get_task(task_id=task["id"]),
                "PROGRAMMER",
            )

            self.assertEqual(updated["status"], "reported")
            self.assertEqual(updated["artifacts"][0]["path"], target_path)

    def test_auto_submit_seed_task_recovers_missing_submit(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source_dir = root / "extracted"
            source_dir.mkdir()
            (source_dir / "demo.py").write_text("print('ok')\n", encoding="utf-8")
            board = TaskBoard(workspace, "test")
            board.add_tasks(
                [
                    {
                        "task_key": "SEED-FILES",
                        "title": "Seed file tasks",
                        "description": "Inventory files and seed one task per file.",
                        "task_type": "coordination",
                        "priority": 1,
                    }
                ]
            )
            seed = board.next_ready()
            board.begin_task(seed["id"], "PROGRAMMER", "Inventory the extracted files")
            board.inventory(
                root="extracted",
                pattern="**/*",
                task_type="analysis",
                title_prefix="Analyze",
                description_template="Analyze {source_path}",
                acceptance_criteria=["Analyzed"],
                suggested_agent="PROGRAMMER",
                priority=10,
            )

            updated = _auto_submit_seed_task(board, board.get_task(task_id=seed["id"]), "PROGRAMMER")

            self.assertEqual(updated["status"], "reported")
            self.assertIn("Seeded", updated["result_summary"])

    def test_cleanup_redundant_collection_tasks_cancels_seed_and_broad_parents(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "src").mkdir()
            (root / "src" / "demo.py").write_text("print('ok')\n", encoding="utf-8")
            board = TaskBoard(workspace, "test")
            board.add_tasks(
                [
                    {
                        "task_key": "SEED-FILES",
                        "title": "Seed file tasks",
                        "description": "Inventory files and seed one task per file.",
                        "task_type": "coordination",
                        "priority": 1,
                    },
                    {
                        "task_key": "GENERATE-ALL",
                        "title": "Generate README for each file",
                        "description": "Create a README for every file in the workspace.",
                        "task_type": "implementation",
                        "priority": 2,
                    },
                    {
                        "task_key": "FILE-SRC-DEMO_PY",
                        "title": "Analyze src/demo.py",
                        "description": "Analyze a concrete file.",
                        "task_type": "documentation",
                        "priority": 3,
                        "source_path": "src/demo.py",
                    },
                ]
            )

            cancelled = _cleanup_redundant_collection_tasks(board)

            self.assertEqual(cancelled, 2)
            self.assertEqual(board.get_task(task_key="SEED-FILES")["status"], "cancelled")
            self.assertEqual(board.get_task(task_key="GENERATE-ALL")["status"], "cancelled")

    def test_invalid_orchestrator_delegation_falls_back_to_first_ready_task(self):
        with tempfile.TemporaryDirectory() as workspace:
            board = TaskBoard(workspace, "test")
            board.add_tasks(
                [
                    {
                        "task_key": "TASK-A",
                        "title": "First",
                        "description": "Do the first task",
                        "task_type": "implementation",
                        "priority": 1,
                        "suggested_agent": "WORKER",
                    }
                ]
            )
            response_model = create_orchestrator_response(["WORKER"])
            caught = None

            def bad_decision(messages):
                nonlocal caught
                try:
                    response_model(action="delegate_to_agent", description="broken")
                except ValidationError as exc:
                    caught = exc
                    raise exc
                raise AssertionError("Expected ValidationError")

            def chat(*args, **kwargs):
                task = board.get_task(task_key="TASK-A")
                board.submit(task["id"], summary="done", evidence="completed", artifacts=[])

            worker = SimpleNamespace(name="WORKER", chat=chat)
            decisions = [SimpleNamespace(action="finish", description="done", task_key=None, agent_name=None)]
            orchestrator = SimpleNamespace(
                plan_tasks=lambda messages: SimpleNamespace(summary="unused", tasks=[]),
                decide_next_action=bad_decision,
                review_task=lambda messages: (
                    SimpleNamespace(outcome="accept", validation_notes="accepted", new_tasks=[])
                    if '"status": "reported"' in messages[-1]["content"]
                    else decisions.pop(0)
                ),
            )
            self.assertIsNone(self.run_loop(workspace, orchestrator, [worker], steps=3))
            self.assertIsNotNone(caught)
            self.assertEqual(board.get_task(task_key="TASK-A")["status"], "validated")

    def test_tiny_zip_readme_flow_uses_generic_task_metadata(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            archive = root / "tiny_sources.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                for idx in range(20):
                    zf.writestr(
                        f"module_{idx}.py",
                        (
                            f"def add_{idx}(value: int) -> int:\n"
                            f"    \"\"\"Return value plus {idx}.\"\"\"\n"
                            f"    return value + {idx}\n"
                        ),
                    )
            (root / "TEMPLATE_README.md").write_text(
                "# {{entity_name}}\n\n## Summary\n\n## Behavior\n\n## Example\n",
                encoding="utf-8",
            )

            board = TaskBoard(workspace, "test")

            class PlannedTask:
                def __init__(self, payload):
                    self.payload = payload

                def model_dump(self, exclude_none=True):
                    return dict(self.payload)

            orchestrator = SimpleNamespace(
                name="ORCHESTRATOR",
                plan_tasks=lambda messages: SimpleNamespace(
                    summary="Extract archive and document each source file.",
                    tasks=[
                        PlannedTask(
                            {
                                "task_key": "EXTRACT_ARCHIVE",
                                "title": "Extract archive",
                                "description": "Extract tiny_sources.zip into extracted/",
                                "task_type": "implementation",
                                "priority": 1,
                                "suggested_agent": "PROGRAMMER",
                                "acceptance_criteria": ["Archive extracted into extracted/"],
                            }
                        ),
                        PlannedTask(
                            {
                                "task_key": "INVENTORY_SOURCES",
                                "title": "Inventory extracted sources",
                                "description": "Create one documentation task per extracted Python file.",
                                "task_type": "coordination",
                                "priority": 2,
                                "depends_on_keys": ["EXTRACT_ARCHIVE"],
                                "suggested_agent": "PROGRAMMER",
                                "acceptance_criteria": ["One file task exists for every source file"],
                            }
                        ),
                    ],
                ),
                decide_next_action=lambda messages: (
                    SimpleNamespace(
                        action="delegate_to_agent",
                        agent_name="PROGRAMMER",
                        task_key=(board.next_ready() or {"task_key": None})["task_key"],
                        description="Process the next ready task",
                    )
                    if board.summary()["remaining"] > 0
                    else SimpleNamespace(action="finish", description="done", task_key=None, agent_name=None)
                ),
                review_task=lambda messages: SimpleNamespace(outcome="accept", validation_notes="accepted", new_tasks=[]),
            )

            def read_json_output(result):
                self.assertTrue(result["ok"], result.get("error"))
                return json.loads(result["output"]) if result["output"] else {}

            def chat(*args, **kwargs):
                current = read_json_output(
                    execute_registered_tool(
                        workspace=workspace,
                        tool_name="task_board",
                        tool_input={"action": "current"},
                        scope="test",
                    )
                )
                task_key = current["task_key"]
                if task_key == "EXTRACT_ARCHIVE":
                    extracted = execute_registered_tool(
                        workspace=workspace,
                        tool_name="workspace_fs",
                        tool_input={
                            "action": "extract_zip",
                            "zip_path": "tiny_sources.zip",
                            "destination": "extracted",
                            "overwrite": False,
                        },
                        scope="test",
                    )
                    self.assertTrue(extracted["ok"], extracted.get("error"))
                    listed = execute_registered_tool(
                        workspace=workspace,
                        tool_name="workspace_fs",
                        tool_input={"action": "list_tree", "root": "extracted", "pattern": "*.py", "max_entries": 30},
                        scope="test",
                    )
                    self.assertTrue(listed["ok"], listed.get("error"))
                    submitted = execute_registered_tool(
                        workspace=workspace,
                        tool_name="task_board",
                        tool_input={
                            "action": "submit",
                            "task_id": current["id"],
                            "summary": "Archive extracted.",
                            "evidence": "tiny_sources.zip extracted into extracted/ with Python files.",
                            "artifacts": ["extracted"],
                        },
                        scope="test",
                    )
                    self.assertTrue(submitted["ok"], submitted.get("error"))
                    return

                if task_key == "INVENTORY_SOURCES":
                    seeded = execute_registered_tool(
                        workspace=workspace,
                        tool_name="task_board",
                        tool_input={
                            "action": "inventory",
                            "task_id": current["id"],
                            "summary": "Analyze {source_path}. Save the primary artifact to {target_path}.",
                            "root": "extracted",
                            "pattern": "*.py",
                            "task_type": "documentation",
                            "title_prefix": "Generate README for",
                            "suggested_agent": "PROGRAMMER",
                            "priority": 10,
                            "acceptance_criteria": ["README.md created", "README saved to target_path"],
                        },
                        scope="test",
                    )
                    self.assertTrue(seeded["ok"], seeded.get("error"))
                    submitted = execute_registered_tool(
                        workspace=workspace,
                        tool_name="task_board",
                        tool_input={
                            "action": "submit",
                            "task_id": current["id"],
                            "summary": "Created one file task per source file.",
                            "evidence": "Inventory completed for extracted/*.py and task board now contains file tasks.",
                            "artifacts": [],
                        },
                        scope="test",
                    )
                    self.assertTrue(submitted["ok"], submitted.get("error"))
                    return

                metadata = current["task_metadata"]
                content_parts = []
                while True:
                    chunk = read_json_output(
                        execute_registered_tool(
                            workspace=workspace,
                            tool_name="task_board",
                            tool_input={"action": "read_source", "task_id": current["id"], "max_chars": 4000},
                            scope="test",
                        )
                    )
                    content_parts.append(chunk["content"])
                    if chunk["eof"]:
                        break
                source_text = "".join(content_parts)
                template = execute_registered_tool(
                    workspace=workspace,
                    tool_name="workspace_fs",
                    tool_input={"action": "read_text", "path": "TEMPLATE_README.md", "max_chars": 4000, "offset": 0},
                    scope="test",
                )
                self.assertTrue(template["ok"], template.get("error"))

                source_name = Path(current["source_path"]).name
                func_name = f"add_{metadata['entity_name'].split('_')[-1]}"
                readme = (
                    f"# {metadata['entity_name']}\n\n"
                    f"## Summary\n\n"
                    f"Source file `{source_name}` defines `{func_name}`.\n\n"
                    f"## Behavior\n\n"
                    f"This function returns the input value plus {metadata['entity_name'].split('_')[-1]}.\n\n"
                    f"## Example\n\n"
                    f"`{func_name}(3)` returns `{3 + int(metadata['entity_name'].split('_')[-1])}`.\n"
                )
                made_dir = execute_registered_tool(
                    workspace=workspace,
                    tool_name="workspace_fs",
                    tool_input={"action": "mkdir", "path": metadata["target_dir"]},
                    scope="test",
                )
                self.assertTrue(made_dir["ok"], made_dir.get("error"))
                write = execute_registered_tool(
                    workspace=workspace,
                    tool_name="workspace_fs",
                    tool_input={
                        "action": "write_text",
                        "path": metadata["target_path"],
                        "content": readme,
                        "append": False,
                    },
                    scope="test",
                )
                self.assertTrue(write["ok"], write.get("error"))
                artifact = execute_registered_tool(
                    workspace=workspace,
                    tool_name="workspace_fs",
                    tool_input={"action": "read_text", "path": metadata["target_path"], "max_chars": 4000, "offset": 0},
                    scope="test",
                )
                self.assertTrue(artifact["ok"], artifact.get("error"))
                self.assertIn(func_name, artifact["output"])
                self.assertIn("return value +", source_text)
                submitted = execute_registered_tool(
                    workspace=workspace,
                    tool_name="task_board",
                    tool_input={
                        "action": "submit",
                        "task_id": current["id"],
                        "summary": f"Created README for {source_name}.",
                        "evidence": f"Wrote {metadata['target_path']} based on full source inspection and template reference.",
                        "artifacts": [metadata["target_path"]],
                    },
                    scope="test",
                )
                self.assertTrue(submitted["ok"], submitted.get("error"))

            worker = SimpleNamespace(name="PROGRAMMER", chat=chat)

            self.assertIsNone(self.run_loop(workspace, orchestrator, [worker], steps=8))
            summary = board.summary()
            self.assertEqual(summary["remaining"], 0)
            readmes = sorted(root.glob("module_*/README.md"))
            self.assertEqual(len(readmes), 20)
            self.assertTrue((root / "module_0" / "README.md").is_file())
            self.assertIn("add_0", (root / "module_0" / "README.md").read_text(encoding="utf-8"))
            self.assertEqual(board.completion_report()["validated_tasks"], 22)

    def test_blocked_task_review_reopens_instead_of_crashing_on_accept(self):
        with tempfile.TemporaryDirectory() as workspace:
            board = TaskBoard(workspace, "test")
            artifact_dir = Path(workspace) / ".agent"
            artifact_dir.mkdir(exist_ok=True)
            artifact = artifact_dir / "report.json"
            artifact.write_text('{"ok": true}', encoding="utf-8")
            board.add_tasks(
                [
                    {
                        "task_key": "TASK-1",
                        "title": "Structure",
                        "description": "Create structure",
                        "task_type": "implementation",
                        "priority": 1,
                    }
                ]
            )
            task = board.next_ready()
            board.begin_task(task["id"], "WORKER", "Do the work")
            board.submit(task["id"], summary="done", evidence="created files", artifacts=[".agent/report.json"])
            board.validate(task["id"], accepted=True, validation_notes="accepted")
            artifact.write_text('{"ok": false}', encoding="utf-8")
            board.verify()

            decisions = [SimpleNamespace(action="finish", description="done", task_key=None, agent_name=None)]
            orchestrator = SimpleNamespace(
                plan_tasks=lambda messages: SimpleNamespace(summary="unused", tasks=[]),
                decide_next_action=lambda messages: decisions[0],
                review_task=lambda messages: SimpleNamespace(outcome="accept", validation_notes="accepted", new_tasks=[]),
            )
            with self.assertRaises(BudgetExhausted):
                self.run_loop(workspace, orchestrator, [], steps=2)
            self.assertEqual(board.get_task(task_id=task["id"])["status"], "ready")


if __name__ == "__main__":
    unittest.main()
