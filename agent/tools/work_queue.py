import json

from agent.work_queue import TaskBoard
from agent.tools.tools_models import Tool, ToolResult


def task_board_executor(
    workspace,
    action,
    task_id=None,
    task_key=None,
    summary="",
    evidence="",
    text="",
    artifacts=None,
    limit=10,
    scope="default",
):
    board = TaskBoard(workspace, scope)
    artifacts = list(artifacts or [])

    if action == "status":
        result = board.summary(limit=int(limit))
    elif action == "current":
        result = board.active_task() or {}
    elif action == "next":
        result = board.next_ready() or {}
    elif action == "get":
        result = board.get_task(task_id=task_id, task_key=task_key) or {}
    elif action == "list":
        statuses = [item.strip() for item in text.split(",") if item.strip()]
        result = board.list_tasks(statuses=statuses or None, limit=int(limit))
    elif action == "submit":
        if task_id is None:
            raise ValueError("task_id is required for submit")
        result = board.submit(
            int(task_id),
            summary=summary,
            evidence=evidence,
            artifacts=artifacts,
            follow_up_suggestions=text,
        )
    elif action == "block":
        if task_id is None:
            raise ValueError("task_id is required for block")
        result = board.block(int(task_id), evidence or summary or text)
    elif action == "reopen":
        if task_id is None:
            raise ValueError("task_id is required for reopen")
        result = board.reopen(int(task_id), text or summary or evidence)
    elif action == "verify":
        result = board.verify()
    else:
        raise ValueError("Unknown task board action")

    return ToolResult(ok=True, output=json.dumps(result, ensure_ascii=False))


TASK_BOARD_TOOL = Tool(
    name="task_board",
    description=(
        "Durable SQLite task board shared by the orchestrator and workers. "
        "Use current/get/status/list to inspect task state. "
        "Use submit to report a finished delegated task with summary, evidence, and artifact paths. "
        "Use block when the task cannot proceed. Use reopen only when retrying a returned task. "
        "verify checks that previously validated artifacts still exist."
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "current", "next", "get", "list", "submit", "block", "reopen", "verify"],
            },
            "task_id": {"type": ["integer", "null"]},
            "task_key": {"type": ["string", "null"]},
            "summary": {"type": "string"},
            "evidence": {"type": "string"},
            "text": {"type": "string"},
            "artifacts": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer"},
        },
        "required": ["action", "task_id", "task_key", "summary", "evidence", "text", "artifacts", "limit"],
        "additionalProperties": False,
    },
    executor=task_board_executor,
)
