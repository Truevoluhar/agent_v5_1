import unittest

from agent.context_guard import ContextLimits, ContextWindowGuard


class ContextGuardTests(unittest.TestCase):

    def test_trim_function_call_outputs_keeps_all_call_ids(self):
        limits = ContextLimits(
            max_input_chars=120,
            max_tool_output_chars=80,
            max_message_chars=80,
            max_system_message_chars=200,
            min_recent_messages=1,
            max_retries=2,
        )
        guard = ContextWindowGuard(limits)

        outputs = [
            {
                "type": "function_call_output",
                "call_id": "call_a",
                "output": "A" * 300,
            },
            {
                "type": "function_call_output",
                "call_id": "call_b",
                "output": "B" * 300,
            },
            {
                "type": "function_call_output",
                "call_id": "call_c",
                "output": "C" * 300,
            },
        ]

        trimmed = guard.trim_function_call_outputs(outputs, attempt=1)

        self.assertEqual(len(trimmed), 3)
        self.assertEqual([item["call_id"] for item in trimmed], ["call_a", "call_b", "call_c"])
        self.assertTrue(all(isinstance(item.get("output"), str) for item in trimmed))


if __name__ == "__main__":
    unittest.main()
