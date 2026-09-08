import unittest

from agent.orchestrator_agent import create_orchestrator_response


class OrchestratorResponseTests(unittest.TestCase):

    def setUp(self):
        self.response_model = create_orchestrator_response(["PLANNER", "PROGRAMMER"])

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
            agent_name="PROGRAMMER",
        )

        self.assertEqual(response.agent_name, "PROGRAMMER")

        with self.assertRaises(ValueError):
            self.response_model(
                action="delegate_to_agent",
                description="Inspect the artifact usage.",
            )


if __name__ == "__main__":
    unittest.main()