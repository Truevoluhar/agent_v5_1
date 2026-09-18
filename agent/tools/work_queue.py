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
    root=".",
    pattern="**/*",
    task_type="implementation",
    title_prefix="Analyze",
    suggested_agent=None,
    priority=50,
    acceptance_criteria=None,
    max_chars=4000,
    parent_task_id=None,
    scope="default",
    task_metadata=None,
):
    board = TaskBoard(workspace, scope)
    artifacts = list(artifacts or [])
    acceptance_criteria = list(acceptance_criteria or [])
    task_metadata = board._coerce_task_metadata(task_metadata)

    if action == "status":
        result = board.summary(limit=int(limit))
    elif action == "current":
        result = board.active_task() or board.get_task(task_id=task_id, task_key=task_key) or {}
    elif action == "next":
        result = board.next_ready() or {}
    elif action == "get":
        result = board.get_task(task_id=task_id, task_key=task_key) or {}
    elif action == "list":
        statuses = [item.strip() for item in text.split(",") if item.strip()]
        result = board.list_tasks(statuses=statuses or None, limit=int(limit))
    elif action == "inventory":
        result = board.inventory(
            root=root,
            pattern=pattern,
            task_type=task_type,
            title_prefix=title_prefix,
            description_template=summary or text or "Analyze {source_path}",
            acceptance_criteria=acceptance_criteria,
            suggested_agent=suggested_agent,
            priority=int(priority),
            created_by="worker",
            parent_task_id=parent_task_id if parent_task_id is not None else task_id,
            task_metadata=task_metadata,
        )
    elif action == "read_source":
        if task_id is None:
            current = board.active_task()
            if not current:
                raise ValueError("task_id is required when there is no active task")
            task_id = int(current["id"])
        result = board.read_source(int(task_id), max_chars=int(max_chars))
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
        "Use inventory to seed one durable task per file for large document or code collections. "
        "Use read_source to read a file task in bounded chunks until eof=true. "
        "Use submit to report a finished delegated task with summary, evidence, and artifact paths. "
        "Use block when the task cannot proceed. Use reopen only when retrying a returned task. "
        "verify checks that previously validated artifacts still exist."
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "current", "next", "get", "list", "inventory", "read_source", "submit", "block", "reopen", "verify"],
            },
            "task_id": {"type": ["integer", "null"]},
            "task_key": {"type": ["string", "null"]},
            "summary": {"type": "string"},
            "evidence": {"type": "string"},
            "text": {"type": "string"},
            "artifacts": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer"},
            "root": {"type": "string"},
            "pattern": {"type": "string"},
            "task_type": {"type": "string"},
            "title_prefix": {"type": "string"},
            "suggested_agent": {"type": ["string", "null"]},
            "priority": {"type": "integer"},
            "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
            "max_chars": {"type": "integer"},
            "parent_task_id": {"type": ["integer", "null"]},
            "task_metadata": {
                "type": ["array", "null"],
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": {"type": ["string", "null"]},
                        "values": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["key", "value", "values"],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "action", "task_id", "task_key", "summary", "evidence", "text", "artifacts", "limit",
            "root", "pattern", "task_type", "title_prefix", "suggested_agent", "priority",
            "acceptance_criteria", "max_chars", "parent_task_id", "task_metadata"
        ],
        "additionalProperties": False,
    },
    executor=task_board_executor,
)
