import os
from pathlib import Path

from agent.tools.tools_models import Tool, ToolResult



def read_plan_executor(workspace: Path, filename: str) -> ToolResult:
    working_dir = str(workspace)
    try:
        with open(f"{working_dir}/{filename}", "r", encoding="utf-8") as f:
            content = f.read()
        return ToolResult(
            ok=True,
            output=content,
            error=None,
            metadata={}
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            output=None,
            error=str(e),
            metadata={}
        )


READ_PLAN_TOOL = Tool(
    name="read_plan",
    description="Read a plan from a PLAN.md file or similar.",
    parameters={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Name of a plan file, usually PLAN.md"}
        },
        "required": ["filename"],
        "additionalProperties": False
    },
    executor=read_plan_executor
)






def create_or_update_plan_executor(
        workspace: Path,
        filename: str,
        action: str,
        content: str
) -> ToolResult:

    working_dir = str(workspace)
    file_path = Path(f"{working_dir}/{filename}")

    
    if action == "create":
        try:
            if not file_path.exists():
                file_path.touch()
                with open(f"{working_dir}/{filename}", "a", encoding="utf-8") as f:
                    f.write(content)
                return ToolResult(
                    ok=True,
                    output="Plan successfully created.",
                    error=None,
                    metadata={}
                )
            else:
                return ToolResult(
                    ok=False,
                    output=None,
                    error="Plan already exists, use `update` action!",
                    metadata={}
                )
        except Exception as e:
            return ToolResult(
                ok=False,
                output=None,
                error=str(e),
                metadata={}
            )
        

    if action == "update":
        if file_path.exists():
            try:
                with open(f"{working_dir}/{filename}", "a", encoding="utf-8") as f:
                    f.write(content)
                return ToolResult(
                    ok=True,
                    output="Plan successfully updated.",
                    error=None,
                    metadata={}
                )
            except Exception as e:
                return ToolResult(
                    ok=False,
                    output=None,
                    error=str(e),
                    metadata={}
                )
        else:
            return ToolResult(
                ok=False,
                output=None,
                error="Plan already exists, use `update` action!",
                metadata={}
            )

CREATE_OR_UPDATE_PLAN_TOOL = Tool(
    name="create_or_update_plan",
    description="Tool for creating or updating a plan. You should ONLY update PLAN.md or similar file with plan, nothing else.",
    parameters={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Filename of plan file, usually PLAN.md"},
            "action": {"type": "string", "enum": ["create", "update"]},
            "content": {"type": "string"}
        },
        "required": ["filename", "action", "content"],
        "additionalProperties": False
    },
    executor=create_or_update_plan_executor
)