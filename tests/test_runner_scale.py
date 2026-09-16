import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agent.execution import BudgetExhausted
from agent.runner import AgentRunner
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
