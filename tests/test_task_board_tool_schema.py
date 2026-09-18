from agent.tools.work_queue import TASK_BOARD_TOOL


def test_task_board_tool_uses_strict_metadata_schema():
    parameters = TASK_BOARD_TOOL.parameters

    assert "task_metadata" in parameters["required"]

    metadata = parameters["properties"]["task_metadata"]
    assert metadata["type"] == ["array", "null"]
    assert metadata["items"]["additionalProperties"] is False
