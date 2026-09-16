import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

from agent.execution import RunCancelled
from agent.work_queue import workspace_file
from agent.tools.tools_models import Tool, ToolResult


def run_shell_executor(workspace: Path, command: str, cwd: str = ".",
                       timeout: int = 20, background: bool = False,
                       is_cancelled=None) -> ToolResult:
    process = None
    try:
        if not 1 <= timeout <= 3600:
            raise ValueError("timeout must be between 1 and 3600 seconds")
        working_dir = workspace_file(workspace, cwd or ".")
        log_dir = workspace_file(workspace, ".agent/shell")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / (uuid.uuid4().hex + ".log")
        with log_path.open("wb") as log_file:
            process = subprocess.Popen(
                command, cwd=working_dir, shell=True, stdin=subprocess.DEVNULL,
                stdout=log_file, stderr=subprocess.STDOUT,
                start_new_session=os.name != "nt",
            )
        metadata = {"cwd": str(working_dir), "pid": process.pid,
                    "background": background, "log_file": str(log_path)}
        if background:
            return ToolResult(ok=True, output=f"Background process started: {process.pid}", metadata=metadata)
        deadline = time.monotonic() + timeout
        failure = None
        cancelled = False
        while process.poll() is None:
            cancelled = bool(is_cancelled and is_cancelled())
            if cancelled or time.monotonic() >= deadline:
                failure = "Cancelled" if cancelled else f"Command timed out after {timeout}s"
                if os.name != "nt":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()
                process.wait()
                break
            time.sleep(0.05)
        if cancelled:
            raise RunCancelled()
        with log_path.open("rb") as log_file:
            output = log_file.read(12000).decode("utf-8", errors="replace")
        metadata.update(exit_code=process.returncode, truncated=log_path.stat().st_size > 12000)
        if metadata["truncated"]:
            output += f"\n[Output truncated; full log: {log_path}]"
        return ToolResult(ok=failure is None and process.returncode == 0,
                          output=output, error=failure or (f"Exit code {process.returncode}" if process.returncode else None),
                          metadata=metadata)
    except RunCancelled:
        raise
    except Exception as exc:
        return ToolResult(ok=False, error=str(exc))


RUN_SHELL_TOOL = Tool(
    name="run_shell",
    description="Run a shell command inside the workspace.",
    parameters={
        "type": "object",
        "properties": {
            "command": { "type": "string" },
            "cwd": { "type": "string", "default": "" },
            "timeout": { "type": "integer", "default": 20},
            "background": { "type": "boolean", "default": False, "description": "Use background for persistent jobs like starting a server." }
        },
        "required": ["command", "cwd", "timeout", "background"],
        "additionalProperties": False
    },
    executor=run_shell_executor
)