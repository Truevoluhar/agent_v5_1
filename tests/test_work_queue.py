import tempfile
import unittest
from pathlib import Path

from agent.work_queue import WorkQueue


class WorkQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.queue = WorkQueue(self.root, 'session')

    def test_objective_and_workspace_lock_survive_reopening(self):
        from agent.execution import workspace_lock
        self.assertEqual(self.queue.objective('Document all sources'), 'Document all sources')
        self.assertIn('Document all sources', WorkQueue(self.root, 'session').objective('Continue'))
        with workspace_lock(self.root):
            with self.assertRaises(RuntimeError):
                with workspace_lock(self.root):
                    pass
        with workspace_lock(self.root):
            pass

    def test_completion_report_contains_verified_output_paths(self):
        import json
        (self.root / 'source.py').write_text('value = 1')
        self.queue.inventory('.', '*.py', 'document')
        task = self.queue.claim()
        self.queue.read(task['id'])
        (self.root / 'actual.md').write_text('value is one')
        self.queue.finish(task['id'], 'Read source and checked output', ['actual.md'])
        report = self.queue.completion_report()
        self.assertEqual(report['artifact_paths'], ['actual.md'])
        self.assertEqual(report['completed_tasks'], 1)
        saved = json.loads((self.root / report['full_report']).read_text())
        self.assertEqual(saved[0]['source'], 'source.py')
        self.assertEqual(saved[0]['artifacts'][0]['path'], 'actual.md')

    def test_thousand_files_resume_and_verify_exact_coverage(self):
        source = self.root / 'src'
        source.mkdir()
        for n in range(1000):
            (source / f'{n}.py').write_text(f'def f{n}(): return {n}\n')
        self.assertEqual(self.queue.inventory('src', '*.py', 'Document each file')['added'], 1000)
        self.assertEqual(self.queue.inventory('src', '*.py', 'Document each file')['added'], 0)
        output = self.root / 'docs'
        output.mkdir()
        for n in range(1000):
            task = self.queue.claim()
            if n == 500:
                self.queue = WorkQueue(self.root, 'session')
                self.assertEqual(self.queue.claim()['id'], task['id'])
            self.assertTrue(self.queue.read(task['id'])['eof'])
            artifact = f'docs/{task["id"]}.md'
            (self.root / artifact).write_text(f'Documentation for {task["source"]}')
            self.queue.finish(task['id'], 'Checked source and output', [artifact])
        state = self.queue.verify()
        self.assertEqual(state['counts'], {'completed': 1000})
        self.assertEqual(state['remaining'], 0)
        self.assertIsNone(self.queue.claim())
        (self.root / 'docs/1.md').unlink()
        self.assertEqual(self.queue.verify()['remaining'], 1)

    def test_requires_full_read_artifact_and_unchanged_source(self):
        (self.root / 'a.py').write_text('x' * 20000)
        self.queue.inventory('.', '*.py', 'document')
        task = self.queue.claim()
        (self.root / 'a.md').write_text('doc')
        self.queue.read(task['id'])
        with self.assertRaises(ValueError):
            self.queue.finish(task['id'], 'checked', ['a.md'])
        while not self.queue.read(task['id'])['eof']:
            pass
        with self.assertRaises(ValueError):
            self.queue.finish(task['id'], 'checked', [])
        (self.root / 'a.py').write_text('changed')
        with self.assertRaises(ValueError):
            self.queue.finish(task['id'], 'checked', ['a.md'])
        self.queue.refresh(task['id'])
        self.queue.claim()
        self.assertEqual(self.queue.read(task['id'])['content'], 'changed')
        self.queue.finish(task['id'], 'checked', ['a.md'])

    def test_failure_retry_limit_and_session_isolation(self):
        self.queue.add('Implement and test')
        for i in range(3):
            task = self.queue.claim()
            self.assertEqual(task['attempts'], i + 1)
            self.queue.fail(task['id'], 'test failed')
        self.assertIsNone(self.queue.claim())
        self.assertEqual(self.queue.summary()['remaining'], 1)
        self.assertEqual(WorkQueue(self.root, 'other-session').summary()['total'], 0)

    def test_paths_cannot_escape_and_unicode_chunk_boundaries(self):
        with self.assertRaises(ValueError):
            self.queue.inventory('../', '*', 'bad')
        (self.root / 'a.py').write_text('é' * 8001, encoding='utf-8')
        self.queue.inventory('.', '*.py', 'read')
        task = self.queue.claim()
        content = ''
        while True:
            chunk = self.queue.read(task['id'], max_chars=7999)
            content += chunk['content']
            if chunk['eof']:
                break
        self.assertEqual(content, 'é' * 8001)


if __name__ == '__main__':
    unittest.main()
