import tempfile
import unittest
from pathlib import Path

from agent.tools.plan import create_or_update_plan_executor, read_plan_executor


class PlanToolTests(unittest.TestCase):

    def test_update_replace_overwrites_instead_of_appending(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            create_result = create_or_update_plan_executor(
                workspace=workspace,
                filename="PLAN.md",
                action="create",
                content="# Execution Plan\n\nfirst",
            )
            self.assertTrue(create_result.ok)

            update_result = create_or_update_plan_executor(
                workspace=workspace,
                filename="PLAN.md",
                action="update",
                content="# Execution Plan\n\nsecond",
                mode="replace",
            )
            self.assertTrue(update_result.ok)

            content = (workspace / "PLAN.md").read_text(encoding="utf-8")
            self.assertIn("second", content)
            self.assertNotIn("first", content)

    def test_update_replace_section_updates_only_requested_heading(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            create_or_update_plan_executor(
                workspace=workspace,
                filename="PLAN.md",
                action="create",
                content=(
                    "# Execution Plan\n\n"
                    "## Metadata\n"
                    "old metadata\n\n"
                    "## Step Tracker\n"
                    "old steps\n"
                ),
            )

            update_result = create_or_update_plan_executor(
                workspace=workspace,
                filename="PLAN.md",
                action="update",
                content="new steps",
                mode="replace_section",
                section_heading="## Step Tracker",
            )
            self.assertTrue(update_result.ok)

            content = (workspace / "PLAN.md").read_text(encoding="utf-8")
            self.assertIn("## Metadata", content)
            self.assertIn("old metadata", content)
            self.assertIn("new steps", content)
            self.assertNotIn("old steps", content)

    def test_create_uses_latest_execution_plan_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            create_result = create_or_update_plan_executor(
                workspace=workspace,
                filename="PLAN.md",
                action="create",
                content=(
                    "# Execution Plan\n\nolder\n\n"
                    "# Execution Plan\n\nlatest"
                ),
            )
            self.assertTrue(create_result.ok)

            content = (workspace / "PLAN.md").read_text(encoding="utf-8")
            self.assertIn("latest", content)
            self.assertNotIn("older", content)

    def test_update_rejects_oversized_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            create_or_update_plan_executor(
                workspace=workspace,
                filename="PLAN.md",
                action="create",
                content="# Execution Plan\n\nbase",
            )

            update_result = create_or_update_plan_executor(
                workspace=workspace,
                filename="PLAN.md",
                action="update",
                content="# Execution Plan\n\n" + ("x" * 5000),
                max_chars=2000,
            )
            self.assertFalse(update_result.ok)
            self.assertIn("Plan too large", update_result.error or "")

    def test_read_plan_truncates_large_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            large_plan = "# Execution Plan\n\n" + ("a" * 30000)
            (workspace / "PLAN.md").write_text(large_plan, encoding="utf-8")

            read_result = read_plan_executor(workspace=workspace, filename="PLAN.md")
            self.assertTrue(read_result.ok)
            self.assertTrue(read_result.metadata.get("truncated"))
            self.assertIn("[TRUNCATED]", read_result.output or "")


if __name__ == "__main__":
    unittest.main()
