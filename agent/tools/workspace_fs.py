from __future__ import annotations

import zipfile
from pathlib import Path

from agent.tools.tools_models import Tool, ToolResult
from agent.work_queue import TaskBoard, workspace_file


def _list_tree(workspace: Path, root: str, pattern: str, max_entries: int) -> ToolResult:
    base = workspace_file(workspace, root or ".")
    if not base.is_dir():
        return ToolResult(ok=False, output=None, error=f"Directory not found: {base}", metadata={})
    entries: list[str] = []
    for path in sorted(base.glob(pattern or "**/*")):
        relative = path.relative_to(workspace)
        if any(part in {".agent", ".git", "node_modules", "venv", "__pycache__"} for part in relative.parts):
            continue
        entries.append(relative.as_posix() + ("/" if path.is_dir() else ""))
    truncated = len(entries) > max_entries
    shown = entries[:max_entries]
    output = "\n".join(shown)
    if truncated:
        output += "\n... [TRUNCATED]"
    return ToolResult(
        ok=True,
        output=output,
        metadata={
            "root": str(base),
            "pattern": pattern,
            "returned_entries": len(shown),
            "total_entries": len(entries),
            "truncated": truncated,
        },
    )


def _read_text(workspace: Path, path: str, max_chars: int, offset: int) -> ToolResult:
    requested_max_chars = int(max_chars)
    max_chars = max(1, min(requested_max_chars, 12000))
    target = workspace_file(workspace, path)
    if not target.is_file():
        return ToolResult(ok=False, output=None, error=f"File not found: {target}", metadata={})
    raw = target.read_bytes()
    encoding = TaskBoard._detect_text_encoding(raw[:32768])
    if encoding is None:
        return ToolResult(ok=False, output=None, error="Binary file detected; read_text supports text files only", metadata={})
    text = raw.decode(encoding, errors="replace")
    next_offset = min(len(text), max(0, offset) + max_chars)
    chunk = text[max(0, offset):next_offset]
    return ToolResult(
        ok=True,
        output=chunk,
        metadata={
            "path": str(target),
            "requested_max_chars": requested_max_chars,
            "applied_max_chars": max_chars,
            "offset": max(0, offset),
            "next_offset": next_offset,
            "eof": next_offset >= len(text),
            "total_chars": len(text),
            "encoding": encoding,
        },
    )


def _write_text(workspace: Path, path: str, content: str, append: bool) -> ToolResult:
    target = workspace_file(workspace, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with target.open(mode, encoding="utf-8") as stream:
        stream.write(content)
    return ToolResult(
        ok=True,
        output=f"Wrote {len(content)} chars to {path}",
        metadata={"path": str(target), "append": append, "chars": len(content)},
    )


def _mkdir(workspace: Path, path: str) -> ToolResult:
    target = workspace_file(workspace, path)
    target.mkdir(parents=True, exist_ok=True)
    return ToolResult(ok=True, output=f"Directory ready: {path}", metadata={"path": str(target)})


def _extract_zip(workspace: Path, zip_path: str, destination: str, overwrite: bool) -> ToolResult:
    archive = workspace_file(workspace, zip_path)
    if not archive.is_file():
        return ToolResult(ok=False, output=None, error=f"Zip file not found: {archive}", metadata={})
    if archive.suffix.lower() != ".zip":
        return ToolResult(ok=False, output=None, error="extract_zip currently supports .zip files only", metadata={})
    target_dir = workspace_file(workspace, destination or ".")
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with zipfile.ZipFile(archive) as zf:
        members = [member for member in zf.infolist() if not member.is_dir()]
        for member in members:
            name = Path(member.filename)
            if name.is_absolute() or ".." in name.parts:
                return ToolResult(ok=False, output=None, error=f"Unsafe archive path: {member.filename}", metadata={})
        for member in members:
            destination_path = workspace_file(target_dir, member.filename)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if destination_path.exists() and not overwrite:
                continue
            with zf.open(member) as src, destination_path.open("wb") as dst:
                dst.write(src.read())
            extracted += 1
    return ToolResult(
        ok=True,
        output=f"Extracted {extracted} files from {zip_path} to {destination}",
        metadata={
            "archive": str(archive),
            "destination": str(target_dir),
            "extracted_files": extracted,
            "overwrite": overwrite,
        },
    )


def workspace_fs_executor(
    workspace: Path,
    action: str,
    path: str = "",
    content: str = "",
    root: str = ".",
    pattern: str = "**/*",
    zip_path: str = "",
    destination: str = "",
    max_entries: int = 500,
    max_chars: int = 12000,
    offset: int = 0,
    append: bool = False,
    overwrite: bool = False,
) -> ToolResult:
    try:
        workspace_path = Path(workspace)
        if action == "list_tree":
            return _list_tree(workspace_path, root, pattern, max_entries)
        if action == "read_text":
            return _read_text(workspace_path, path, max_chars, offset)
        if action == "write_text":
            return _write_text(workspace_path, path, content, append)
        if action == "mkdir":
            return _mkdir(workspace_path, path)
        if action == "extract_zip":
            return _extract_zip(workspace_path, zip_path, destination, overwrite)
        return ToolResult(ok=False, output=None, error="Unknown workspace_fs action", metadata={})
    except Exception as exc:
        return ToolResult(ok=False, output=None, error=str(exc), metadata={})


WORKSPACE_FS_TOOL = Tool(
    name="workspace_fs",
    description=(
        "Safe workspace filesystem helper. Prefer this over run_shell for bulk archive extraction, "
        "directory listing, bounded text reads, directory creation, and writing text files."
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list_tree", "read_text", "write_text", "mkdir", "extract_zip"]},
            "path": {"type": "string"},
            "content": {"type": "string"},
            "root": {"type": "string"},
            "pattern": {"type": "string"},
            "zip_path": {"type": "string"},
            "destination": {"type": "string"},
            "max_entries": {"type": "integer"},
            "max_chars": {"type": "integer"},
            "offset": {"type": "integer"},
            "append": {"type": "boolean"},
            "overwrite": {"type": "boolean"},
        },
        "required": [
            "action", "path", "content", "root", "pattern", "zip_path", "destination",
            "max_entries", "max_chars", "offset", "append", "overwrite"
        ],
        "additionalProperties": False,
    },
    executor=workspace_fs_executor,
)
