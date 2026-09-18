import unittest

from agent.orchestrator_agent import create_orchestrator_response, create_task_planning_response


class OrchestratorResponseTests(unittest.TestCase):

    def setUp(self):
        self.response_model = create_orchestrator_response(["PLANNER", "PROGRAMMER"])
        self.planning_model = create_task_planning_response(["PLANNER", "PROGRAMMER"])

    def test_finish_ignores_stale_delegated_agent_name(self):
        response = self.response_model(
            action="finish",
            description="The requested analysis is complete.",
            agent_name="PLANNER",
        )

        self.assertEqual(response.agent_name, None)

    def test_ask_user_ignores_stale_delegated_agent_name(self):
        response = self.response_model(
            action="ask_user",
            description="Which environment should be checked next?",
            agent_name="PROGRAMMER",
        )

        self.assertEqual(response.agent_name, None)

    def test_delegation_requires_a_valid_agent_name(self):
        response = self.response_model(
            action="delegate_to_agent",
            description="Inspect the artifact usage.",
            task_key="TASK-1",
            agent_name="PROGRAMMER",
        )

        self.assertEqual(response.agent_name, "PROGRAMMER")
        self.assertEqual(response.task_key, "TASK-1")

        with self.assertRaises(ValueError):
            self.response_model(
                action="delegate_to_agent",
                description="Inspect the artifact usage.",
            )

    def test_planned_task_allows_structured_metadata_entries(self):
        response = self.planning_model(
            summary="Create one task.",
            tasks=[
                {
                    "task_key": "TASK-1",
                    "title": "Document file",
                    "description": "Write the output.",
                    "task_type": "documentation",
                    "priority": 1,
                    "task_metadata": [
                        {"key": "target_path", "value": "docs/README.md"},
                        {"key": "reference_paths", "values": ["TEMPLATE_README.md"]},
                    ],
                    "suggested_agent": "PROGRAMMER",
                }
            ],
        )
        task = response.tasks[0]
        self.assertEqual(task.task_metadata[0].key, "target_path")
        self.assertEqual(task.task_metadata[0].value, "docs/README.md")
        self.assertEqual(task.task_metadata[1].values, ["TEMPLATE_README.md"])

    def test_planned_task_metadata_tolerates_both_value_and_values(self):
        response = self.planning_model(
            summary="Create one task.",
            tasks=[
                {
                    "task_key": "TASK-1",
                    "title": "Extract archive",
                    "description": "Unpack files.",
                    "task_type": "implementation",
                    "priority": 1,
                    "task_metadata": [
                        {"key": "zip_path", "value": "tiny_sources.zip", "values": ["extracted"]},
                    ],
                    "suggested_agent": "PROGRAMMER",
                }
            ],
        )
        task = response.tasks[0]
        self.assertEqual(task.task_metadata[0].key, "zip_path")
        self.assertEqual(task.task_metadata[0].value, "tiny_sources.zip")
        self.assertEqual(task.task_metadata[0].values, ["extracted"])

    def test_planned_task_metadata_drops_empty_entries(self):
        response = self.planning_model(
            summary="Create one task.",
            tasks=[
                {
                    "task_key": "TASK-1",
                    "title": "Document source file",
                    "description": "Create one README.",
                    "task_type": "documentation",
                    "priority": 1,
                    "task_metadata": [
                        {"key": "source_file_path", "value": None, "values": []},
                        {"key": "target_path", "value": "core/README.md", "values": []},
                    ],
                    "suggested_agent": "PROGRAMMER",
                }
            ],
        )
        task = response.tasks[0]
        self.assertEqual(len(task.task_metadata), 1)
        self.assertEqual(task.task_metadata[0].key, "target_path")


if __name__ == "__main__":
    unittest.main()
