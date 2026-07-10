from pathlib import Path
import subprocess

from agent.tools.tools_models import Tool, ToolResult

def run_shell_executor(
    workspace: Path,
    command: str,
    cwd: str = ".",
    timeout: int = 20
) -> ToolResult:
    
    try:
        working_dir = str(workspace)

        completed = subprocess.run(
            command,
            cwd=working_dir,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout
        )

        output = ""
        if completed.stdout:
            output += completed.stdout
        if completed.stderr:
            output += f"\n[stderr] {completed.stderr}"
        
        return ToolResult(
            ok=completed.returncode == 0,
            output=output,
            error=None if completed.returncode == 0 else f"Exit code {completed.returncode}",
            metadata={
                "command": command,
                "cwd": cwd,
                "exit_code": completed.returncode,
            }
        )
    
    except subprocess.TimeoutExpired as e:
        return ToolResult(ok=False, error=str(e))
    except Exception as e:
        return ToolResult(ok=False, error=str(e))
    

RUN_SHELL_TOOL = Tool(
    name="run_shell",
    description="Run a shell command inside the workspace.",
    parameters={
        "type": "object",
        "properties": {
            "command": { "type": "string" },
            "cwd": { "type": "string", "default": "" },
            "timeout": { "type": "integer", "default": 20}
        },
        "required": ["command"]
    },
    executor=run_shell_executor
)