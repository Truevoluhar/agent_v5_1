import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agent.execution import BudgetExhausted
from agent.runner import AgentRunner, _prepare_plan_for_new_session, _read_active_plan_context
from agent.work_queue import WorkQueue


class SessionStub:
    id = 'test'
    messages = []

    def __init__(self):
        self.messages = [{'role': 'user', 'content': 'Do all tasks'}]

    def add_message(self, message):
        self.messages.append(message)

    def get_bounded_context(self, **kwargs):
        return list(self.messages)

    def format_retrieval_context(self, **kwargs):
        return ''


class RunnerScaleTests(unittest.TestCase):
    def test_session_title_is_local_bounded_and_readable(self):
        title = AgentRunner._generate_session_name(
            "# Inspect **one thousand** files and create `README.md` for each"
        )
        self.assertEqual(title, "Inspect one thousand files and create README.md for")
        self.assertLessEqual(len(title.split()), 8)

    def test_empty_prompt_uses_default_session_title(self):
        self.assertEqual(AgentRunner._generate_session_name("  \n"), "New chat")

    def test_new_session_archives_another_sessions_active_plan(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / 'PLAN.md').write_text('# Old task', encoding='utf-8')
            result = _prepare_plan_for_new_session(workspace, 'new-session')
            self.assertFalse((root / 'PLAN.md').exists())
            self.assertEqual(Path(result['archived_to']).read_text(encoding='utf-8'), '# Old task')

            (root / 'PLAN.md').write_text('# New task', encoding='utf-8')
            self.assertEqual(_read_active_plan_context(workspace, 'new-session')[0], '# New task')
            self.assertIsNone(_read_active_plan_context(workspace, 'other-session')[0])

    def run_loop(self, workspace, decision, agents=None, steps=2):
        orchestrator = SimpleNamespace(chat_structured=lambda **kwargs: decision)
        emitter = SimpleNamespace(emit=lambda *args: None)
        return AgentRunner.__new__(AgentRunner)._run_loop(
            session=SessionStub(), config={'max_steps': steps}, agents=agents or [],
            orchestrator_agent=orchestrator, response_agent=None,
            agent_workspace=workspace, orchestrator_context_budget=10000,
            delegated_context_budget=10000, response_context_budget=10000,
            response_schema_source=None, emitter=emitter,
            wait_for_input=lambda question: '', is_cancelled=lambda: False,
        )

    def test_finish_is_rejected_when_queue_is_incomplete(self):
        with tempfile.TemporaryDirectory() as workspace:
            WorkQueue(workspace, 'test').add('unfinished')
            with self.assertRaises(BudgetExhausted):
                self.run_loop(workspace, SimpleNamespace(action='finish', description='done'))

    def test_step_limit_is_not_success(self):
        with tempfile.TemporaryDirectory() as workspace:
            with self.assertRaises(BudgetExhausted):
                self.run_loop(workspace, SimpleNamespace(action='delegate_to_agent', agent_name='none', description='working'))

    def test_worker_budget_yields_and_next_batch_can_finish(self):
        with tempfile.TemporaryDirectory() as workspace:
            queue = WorkQueue(workspace, 'test')
            queue.add('work')
            calls = []
            def chat(*args, **kwargs):
                calls.append(1)
                if len(calls) == 1:
                    raise BudgetExhausted()
                task = queue.claim()
                queue.finish(task['id'], 'validated', [])
            worker = SimpleNamespace(name='WORKER', chat=chat)
            decision = SimpleNamespace(action='delegate_to_agent', agent_name='WORKER', description='continue')
            with self.assertRaises(BudgetExhausted):
                self.run_loop(workspace, decision, [worker])
            self.assertEqual(len(calls), 2)
            self.assertEqual(queue.summary()['remaining'], 0)
            self.assertIsNone(self.run_loop(workspace, SimpleNamespace(action='finish', description='done')))

    def test_delegation_creates_a_durable_task_and_passes_it_to_worker(self):
        with tempfile.TemporaryDirectory() as workspace:
            captured = []
            def chat(messages, *args, **kwargs):
                captured.extend(messages)
                queue = WorkQueue(workspace, 'test')
                task = queue.claim()
                queue.finish(task['id'], 'implemented and checked', [])
            worker = SimpleNamespace(name='WORKER', chat=chat)
            decision = SimpleNamespace(action='delegate_to_agent', agent_name='WORKER', description='Implement the change')
            with self.assertRaises(BudgetExhausted):
                self.run_loop(workspace, decision, [worker], steps=1)
            self.assertEqual(WorkQueue(workspace, 'test').summary()['counts'], {'completed': 1})
            worker_prompt = captured[-1]['content']
            self.assertIn('Implement the change', worker_prompt)
            self.assertIn("work_queue(action='next')", worker_prompt)
