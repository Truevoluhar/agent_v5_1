import json
import tempfile
import unittest
from pathlib import Path

from agent.response_agent import create_dynamic_response_model, load_response_schema


class ResponseAgentTests(unittest.TestCase):

    def test_creates_pydantic_model_from_json_schema_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_path = Path(temp_dir) / "response_schema.json"
            schema_path.write_text(
                json.dumps(
                    {
                        "title": "TaskResponse",
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["completed", "blocked"],
                            },
                            "follow_up_tasks": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["summary", "status"],
                    }
                ),
                encoding="utf-8",
            )

            model = create_dynamic_response_model(schema_path)
            instance = model(summary="done", status="completed")

            self.assertEqual(instance.summary, "done")
            self.assertEqual(instance.status, "completed")
            self.assertEqual(instance.follow_up_tasks, None)

    def test_loads_schema_from_inline_json_string(self):
        raw_schema = json.dumps(
            {
                "title": "InlineResponse",
                "type": "object",
                "properties": {
                    "result": {"type": "string"},
                    "ok": {"type": "boolean"},
                },
                "required": ["result"],
            }
        )

        schema = load_response_schema(raw_schema)
        self.assertEqual(schema["title"], "InlineResponse")
        self.assertEqual(schema["properties"]["result"]["type"], "string")


if __name__ == "__main__":
    unittest.main()
