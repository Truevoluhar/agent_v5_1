import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agent.execution import BudgetExhausted
from agent.runner import AgentRunner
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


if __name__ == "__main__":
    unittest.main()
