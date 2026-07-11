import os
from pathlib import Path
import subprocess

from agent.tools.tools_models import Tool, ToolResult

def run_shell_executor(
    workspace: Path,
    command: str,
    cwd: str = ".",
    timeout: int = 20,
    background: bool = False
) -> ToolResult:
    
    try:
        working_dir = str(workspace)

        if background:
            log_path = "background-process.log"
            log_file = open(log_path, "a", encoding="utf-8")

            kwargs = {
                "cwd": working_dir,
                "shell": True,
                "stdin": subprocess.DEVNULL,
                "stdout": log_file,
                "stderr": subprocess.STDOUT
            }

            if os.name == "nt":
                kwargs["creationflags"] = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
            else:
                kwargs["start_new_session"] = True
            
            process = subprocess.Popen(command, **kwargs)

            return ToolResult(
                ok=True,
                output=f"Background process started with PID {process.pid}",
                error=None,
                metadata={
                    "command": command,
                    "cwd": working_dir,
                    "pid": process.pid,
                    "background": True,
                    "log_file": str(log_path)
                }
            )

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
                "background": False
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
            "timeout": { "type": "integer", "default": 20},
            "background": { "type": "boolean", "default": "false", "description": "Use background for persistent jobs like starting a server." }
        },
        "required": ["command"]
    },
    executor=run_shell_executor
)