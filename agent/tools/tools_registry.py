from agent.execution import RunCancelled
from agent.work_queue import TaskBoard
from dataclasses import dataclass
from typing import Optional, Callable

from agent.tools.tools_models import Tool, ToolResult
from agent.tools.work_queue import TASK_BOARD_TOOL
from agent.tools.workspace_fs import WORKSPACE_FS_TOOL
from agent.tools.shell import RUN_SHELL_TOOL
from agent.tools.drawio import READ_DRAWIO_REFERENCE_TOOL, UPSERT_DRAWIO_DIAGRAM_TOOL
from agent.tools.git_repo import GIT_REPO_BROWSER_TOOL
from agent.tools.najdiAsset import NAJDI_ASSET_TOOL
from agent.tools.getAssetWhereUsed import GET_ASSET_WHERE_USED_TOOL

TOOLS = {
    tool.name: tool for tool in [
        TASK_BOARD_TOOL,
        WORKSPACE_FS_TOOL,
        RUN_SHELL_TOOL,
        READ_DRAWIO_REFERENCE_TOOL,
        UPSERT_DRAWIO_DIAGRAM_TOOL,
        GIT_REPO_BROWSER_TOOL,
        NAJDI_ASSET_TOOL,
        GET_ASSET_WHERE_USED_TOOL
    ]
}



    
def execute_registered_tool(
        workspace: str,
        tool_name: str,
        tool_input: dict,
        scope: str = "default",
        is_cancelled=None,
) -> dict:
    
    tool = TOOLS.get(tool_name)

    if tool is None:
        return {
            "ok": False,
            "error": f"Unknown tool: {tool_name}",
            "output": None,
            "metadata": None
        }
    
    try:

        executor_kwargs = dict(tool_input)
        if tool_name == "task_board":
            executor_kwargs["scope"] = scope

        if tool_name == "run_shell":
            active_task = TaskBoard(workspace, scope).active_task()
            if active_task is None:
                return {
                    "ok": False,
                    "output": None,
                    "error": (
                        "A delegated task must already be in progress before shell execution. "
                        "Inspect it with task_board action='current' and submit or block it when done."
                    ),
                    "metadata": {},
                }
            executor_kwargs["is_cancelled"] = is_cancelled

        result = tool.executor(workspace=workspace, **executor_kwargs)

        return {
            "ok": result.ok,
            "output": result.output,
            "error": result.error,
            "metadata": result.metadata or {}
        }

    except RunCancelled:
        raise
    except TypeError as e:
        return {
            "ok": False,
            "output": None,
            "error": f"Invalid tool input: {str(e)}",
            "metadata": {}
        }
    except Exception as e:
        return {
            "ok": False,
            "output": None,
            "error": str(e),
            "metadata": {}
        }
    

def get_tool_schemas() -> dict:
    return [tool.schema() for tool in TOOLS.values()]
