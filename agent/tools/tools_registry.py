from dataclasses import dataclass
from typing import Optional, Callable

from agent.tools.tools_models import Tool, ToolResult
from agent.tools.shell import RUN_SHELL_TOOL
from agent.tools.plan import READ_PLAN_TOOL, CREATE_OR_UPDATE_PLAN_TOOL


TOOLS = {
    tool.name: tool for tool in [
        RUN_SHELL_TOOL,
        READ_PLAN_TOOL,
        CREATE_OR_UPDATE_PLAN_TOOL
    ]
}



    
def execute_registered_tool(
        workspace: str,
        tool_name: str,
        tool_input: dict
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

        result = tool.executor(workspace=workspace, **executor_kwargs)

        return {
            "ok": result.ok,
            "output": result.output,
            "error": result.error,
            "metadata": result.metadata or {}
        }

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
            "error": {str(e)},
            "metadata": {}
        }
    

def get_tool_schemas() -> dict:
    return [tool.schema() for tool in TOOLS.values()]