import tempfile
import unittest
from pathlib import Path

from agent.execution import RunCancelled
from agent.tools.shell import run_shell_executor


class ShellTests(unittest.TestCase):
    def test_working_directory_and_bounded_output(self):
        with tempfile.TemporaryDirectory() as workspace:
            (Path(workspace) / 'sub').mkdir()
            result = run_shell_executor(workspace, 'pwd', cwd='sub')
            self.assertTrue(result.ok)
            self.assertEqual(result.output.strip(), str(Path(workspace) / 'sub'))
            result = run_shell_executor(workspace, "head -c 50000 /dev/zero")
            self.assertTrue(result.ok)
            self.assertTrue(result.metadata['truncated'])
            self.assertLess(len(result.output), 13000)
            self.assertEqual(Path(result.metadata['log_file']).stat().st_size, 50000)

    def test_timeout_and_cancellation(self):
        with tempfile.TemporaryDirectory() as workspace:
            result = run_shell_executor(workspace, 'sleep 30', timeout=1)
            self.assertFalse(result.ok)
            self.assertIn('timed out', result.error)
            with self.assertRaises(RunCancelled):
                run_shell_executor(workspace, 'sleep 30', is_cancelled=lambda: True)

    def test_cwd_cannot_escape(self):
        with tempfile.TemporaryDirectory() as workspace:
            self.assertFalse(run_shell_executor(workspace, 'pwd', cwd='..').ok)
