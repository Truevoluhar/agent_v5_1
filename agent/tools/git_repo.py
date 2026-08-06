from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
import re
import subprocess

from agent.tools.tools_models import Tool, ToolResult


DEFAULT_CLONE_ROOT = "cloned_repos"
DEFAULT_MAX_ENTRIES = 500
DEFAULT_MAX_CHARS = 12_000


def _resolve_workspace_path(workspace: Path, relative_path: str) -> Path:
    workspace_path = Path(workspace).resolve()
    target = (workspace_path / relative_path).resolve()

    if workspace_path != target and workspace_path not in target.parents:
        raise ValueError("Path must stay inside the workspace")

    return target


def _slugify_repo_name(raw_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_name).strip("-._")
    return cleaned or "repo"


def _derive_repo_name(repo_url: str) -> str:
    # Handle URLs, SSH-style remotes, and local filesystem paths.
    if ":" in repo_url and not repo_url.startswith(("http://", "https://", "file://", "/", "./", "../")):
        # git@github.com:owner/repo.git
        suffix = repo_url.split(":", 1)[1]
        name = suffix.rstrip("/").split("/")[-1]
    else:
        parsed = urlparse(repo_url)
        if parsed.scheme in {"http", "https", "file", "ssh", "git"}:
            name = parsed.path.rstrip("/").split("/")[-1]
        else:
            name = Path(repo_url).name

    if name.endswith(".git"):
        name = name[:-4]

    return _slugify_repo_name(name)


def _clone_repo(
    workspace: Path,
    repo_url: str,
    repo_name: str | None,
    clone_root: str,
    branch: str | None,
    depth: int,
    timeout: int,
) -> ToolResult:
    if not repo_url.strip():
        return ToolResult(ok=False, output=None, error="repo_url is required for action='clone'", metadata={})

    resolved_root = _resolve_workspace_path(workspace, clone_root)
    resolved_root.mkdir(parents=True, exist_ok=True)

    final_repo_name = _slugify_repo_name(repo_name) if repo_name else _derive_repo_name(repo_url)
    destination = _resolve_workspace_path(workspace, str(Path(clone_root) / final_repo_name))

    if destination.exists():
        if (destination / ".git").exists():
            return ToolResult(
                ok=True,
                output="Repository already exists in workspace.",
                error=None,
                metadata={
                    "repo_url": repo_url,
                    "repo_name": final_repo_name,
                    "repo_dir": str(destination),
                    "already_exists": True,
                },
            )
        return ToolResult(
            ok=False,
            output=None,
            error=f"Destination exists and is not a git repository: {destination}",
            metadata={},
        )

    cmd = ["git", "clone"]
    if depth > 0:
        cmd.extend(["--depth", str(depth)])
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([repo_url, str(destination)])

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(workspace),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return ToolResult(ok=False, output=None, error=f"git clone timed out: {exc}", metadata={})
    except Exception as exc:
        return ToolResult(ok=False, output=None, error=str(exc), metadata={})

    combined_output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    if completed.returncode != 0:
        return ToolResult(
            ok=False,
            output=combined_output.strip() or None,
            error=f"git clone failed with exit code {completed.returncode}",
            metadata={
                "repo_url": repo_url,
                "repo_name": final_repo_name,
                "repo_dir": str(destination),
            },
        )

    return ToolResult(
        ok=True,
        output=(combined_output.strip() or "Repository cloned successfully."),
        error=None,
        metadata={
            "repo_url": repo_url,
            "repo_name": final_repo_name,
            "repo_dir": str(destination),
            "already_exists": False,
        },
    )


def _list_repo_files(
    workspace: Path,
    repo_dir: str,
    recursive: bool,
    include_hidden: bool,
    max_entries: int,
) -> ToolResult:
    if not repo_dir:
        return ToolResult(ok=False, output=None, error="repo_dir is required for action='list_files'", metadata={})

    resolved_repo = _resolve_workspace_path(workspace, repo_dir)
    if not resolved_repo.exists() or not resolved_repo.is_dir():
        return ToolResult(ok=False, output=None, error=f"Repository directory not found: {resolved_repo}", metadata={})

    entries: list[str] = []

    if recursive:
        iterator = resolved_repo.rglob("*")
    else:
        iterator = resolved_repo.iterdir()

    for path in iterator:
        relative = path.relative_to(resolved_repo)
        parts = relative.parts

        if not include_hidden and any(part.startswith(".") for part in parts):
            continue

        text = str(relative)
        if path.is_dir():
            text += "/"

        entries.append(text)

    entries.sort()
    truncated = len(entries) > max_entries
    shown_entries = entries[:max_entries]

    output = "\n".join(shown_entries)
    if truncated:
        output += "\n... [TRUNCATED]"

    return ToolResult(
        ok=True,
        output=output,
        error=None,
        metadata={
            "repo_dir": str(resolved_repo),
            "recursive": recursive,
            "include_hidden": include_hidden,
            "total_entries": len(entries),
            "returned_entries": len(shown_entries),
            "truncated": truncated,
        },
    )


def _read_repo_file(
    workspace: Path,
    repo_dir: str,
    file_path: str,
    max_chars: int,
) -> ToolResult:
    if not repo_dir:
        return ToolResult(ok=False, output=None, error="repo_dir is required for action='read_file'", metadata={})
    if not file_path:
        return ToolResult(ok=False, output=None, error="file_path is required for action='read_file'", metadata={})

    resolved_repo = _resolve_workspace_path(workspace, repo_dir)
    if not resolved_repo.exists() or not resolved_repo.is_dir():
        return ToolResult(ok=False, output=None, error=f"Repository directory not found: {resolved_repo}", metadata={})

    target = (resolved_repo / file_path).resolve()
    if resolved_repo != target and resolved_repo not in target.parents:
        return ToolResult(ok=False, output=None, error="file_path must stay inside repo_dir", metadata={})

    if not target.exists() or not target.is_file():
        return ToolResult(ok=False, output=None, error=f"File not found: {target}", metadata={})

    raw = target.read_bytes()
    if b"\x00" in raw[:4096]:
        return ToolResult(ok=False, output=None, error="Binary file detected; read_file supports text files only", metadata={})

    text = raw.decode("utf-8", errors="replace")
    truncated = False
    if max_chars > 0 and len(text) > max_chars:
        text = text[:max_chars] + "\n\n[TRUNCATED]"
        truncated = True

    return ToolResult(
        ok=True,
        output=text,
        error=None,
        metadata={
            "repo_dir": str(resolved_repo),
            "file": str(target),
            "chars": len(text),
            "truncated": truncated,
            "max_chars": max_chars,
        },
    )


def git_repo_browser_executor(
    workspace: Path,
    action: str,
    repo_url: str | None = None,
    repo_name: str | None = None,
    repo_dir: str | None = None,
    file_path: str | None = None,
    clone_root: str = DEFAULT_CLONE_ROOT,
    branch: str | None = None,
    depth: int = 1,
    recursive: bool = True,
    include_hidden: bool = False,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    max_chars: int = DEFAULT_MAX_CHARS,
    timeout: int = 120,
) -> ToolResult:
    try:
        workspace_path = Path(workspace)

        if action == "clone":
            return _clone_repo(
                workspace=workspace_path,
                repo_url=repo_url or "",
                repo_name=repo_name,
                clone_root=clone_root,
                branch=branch,
                depth=depth,
                timeout=timeout,
            )

        if action == "list_files":
            return _list_repo_files(
                workspace=workspace_path,
                repo_dir=repo_dir or "",
                recursive=recursive,
                include_hidden=include_hidden,
                max_entries=max_entries,
            )

        if action == "read_file":
            return _read_repo_file(
                workspace=workspace_path,
                repo_dir=repo_dir or "",
                file_path=file_path or "",
                max_chars=max_chars,
            )

        return ToolResult(
            ok=False,
            output=None,
            error="action must be one of: clone, list_files, read_file",
            metadata={},
        )
    except Exception as exc:
        return ToolResult(ok=False, output=None, error=str(exc), metadata={})


GIT_REPO_BROWSER_TOOL = Tool(
    name="git_repo_browser",
    description=(
        "Clone a git repository and browse/read files from the cloned copy. "
        "Use action='clone' first, then action='list_files' and action='read_file'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["clone", "list_files", "read_file"],
            },
            "repo_url": {
                "type": ["string", "null"],
                "description": "Git URL for clone action.",
            },
            "repo_name": {
                "type": ["string", "null"],
                "description": "Optional destination folder name for clone action.",
            },
            "repo_dir": {
                "type": ["string", "null"],
                "description": "Relative path to the cloned repo directory for list/read actions.",
            },
            "file_path": {
                "type": ["string", "null"],
                "description": "Relative path inside repo_dir for read_file action.",
            },
            "clone_root": {
                "type": "string",
                "description": "Workspace-relative directory where repositories are cloned.",
                "default": DEFAULT_CLONE_ROOT,
            },
            "branch": {
                "type": ["string", "null"],
                "description": "Optional branch name for clone action.",
            },
            "depth": {
                "type": "integer",
                "description": "Shallow clone depth. Use 0 or negative for full history.",
                "default": 1,
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether list_files should recurse through subdirectories.",
                "default": True,
            },
            "include_hidden": {
                "type": "boolean",
                "description": "Whether list_files should include hidden files and directories.",
                "default": False,
            },
            "max_entries": {
                "type": "integer",
                "description": "Maximum listed entries for list_files output.",
                "default": DEFAULT_MAX_ENTRIES,
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters returned by read_file.",
                "default": DEFAULT_MAX_CHARS,
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds for clone action.",
                "default": 120,
            },
        },
        "required": [
            "action",
            "repo_url",
            "repo_name",
            "repo_dir",
            "file_path",
            "clone_root",
            "branch",
            "depth",
            "recursive",
            "include_hidden",
            "max_entries",
            "max_chars",
            "timeout",
        ],
        "additionalProperties": False,
    },
    executor=git_repo_browser_executor,
)
