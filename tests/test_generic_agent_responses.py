import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


try:
    import openai  # noqa: F401
except ModuleNotFoundError:
    openai_stub = types.ModuleType("openai")

    class OpenAIStub:
        def __init__(self, **kwargs):
            pass

    openai_stub.OpenAI = OpenAIStub
    openai_stub.DefaultHttpx2Client = lambda **kwargs: None
    sys.modules["openai"] = openai_stub

from agent.generic_agent import GenericAgent


class FakeResponsesClient:
    def __init__(self, responses):
        self.responses = self
        self.pending_responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.pending_responses.pop(0)


class FakeSession:
    def __init__(self):
        self.messages = []

    def add_message(self, message):
        self.messages.append(message)


def response(output, output_text=""):
    return SimpleNamespace(
        id="resp_test",
        output=output,
        output_text=output_text,
        status="completed",
    )


class GenericAgentResponsesTests(unittest.TestCase):
    def make_agent(self, client):
        with tempfile.TemporaryDirectory() as temp_dir:
            resources = Path(temp_dir) / "resources" / "TEST"
            resources.mkdir(parents=True)
            (resources / "AGENT.md").write_text("agent", encoding="utf-8")
            (resources / "SKILLS.md").write_text("skills", encoding="utf-8")

            agent = GenericAgent(
                id=1,
                name="TEST",
                model="test-model",
                api_key="test-key",
                base_url="http://test.invalid",
                temperature=0,
                resources_path=str(Path(temp_dir) / "resources"),
                workspace_path=temp_dir,
            )

        agent.client = client
        return agent

    def test_tool_continuation_is_self_contained_and_stateless(self):
        reasoning = SimpleNamespace(type="reasoning", id="reason_1")
        function_call = SimpleNamespace(
            type="function_call",
            name="test_tool",
            arguments=json.dumps({"value": "input"}),
            call_id="call_1",
        )
        first_response = response([reasoning, function_call])
        final_response = response([], output_text="done")
        client = FakeResponsesClient([first_response, final_response])
        agent = self.make_agent(client)
        session = FakeSession()

        with patch("agent.generic_agent.get_tool_schemas", return_value=[]), patch(
            "agent.generic_agent.execute_registered_tool",
            return_value={"ok": True, "output": "tool result"},
        ):
            result = agent.chat(
                [{"role": "user", "content": "use the tool"}],
                session,
            )

        self.assertEqual(result, "done")
        self.assertEqual(len(client.calls), 2)
        self.assertIs(client.calls[0]["store"], False)
        second_call = client.calls[1]
        self.assertNotIn("previous_response_id", second_call)
        self.assertIs(second_call["store"], False)
        self.assertEqual(second_call["input"][0], {"role": "user", "content": "use the tool"})
        self.assertIn(reasoning, second_call["input"])
        self.assertIn(function_call, second_call["input"])
        self.assertIn(
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": '{"ok": true, "output": "tool result"}',
            },
            second_call["input"],
        )
        self.assertEqual(session.messages, [{"role": "assistant", "content": "done"}])

    def test_multiple_tool_rounds_carry_each_response_once(self):
        call_a = SimpleNamespace(
            type="function_call",
            name="tool_a",
            arguments="{}",
            call_id="call_a",
        )
        call_b = SimpleNamespace(
            type="function_call",
            name="tool_b",
            arguments="{}",
            call_id="call_b",
        )
        output_a = [
            SimpleNamespace(type="reasoning", id="reason_a"),
            call_a,
        ]
        output_b = [
            SimpleNamespace(type="reasoning", id="reason_b"),
            call_b,
        ]
        client = FakeResponsesClient(
            [response(output_a), response(output_b), response([], output_text="done")]
        )
        agent = self.make_agent(client)
        session = FakeSession()

        with patch("agent.generic_agent.get_tool_schemas", return_value=[]), patch(
            "agent.generic_agent.execute_registered_tool",
            side_effect=[{"round": "a"}, {"round": "b"}],
        ):
            self.assertEqual(
                agent.chat([{"role": "user", "content": "start"}], session),
                "done",
            )

        third_input = client.calls[2]["input"]
        self.assertEqual(
            third_input,
            [
                {"role": "user", "content": "start"},
                *output_a,
                {
                    "type": "function_call_output",
                    "call_id": "call_a",
                    "output": '{"round": "a"}',
                },
                *output_b,
                {
                    "type": "function_call_output",
                    "call_id": "call_b",
                    "output": '{"round": "b"}',
                },
            ],
        )
        self.assertNotIn("previous_response_id", client.calls[2])


if __name__ == "__main__":
    unittest.main()