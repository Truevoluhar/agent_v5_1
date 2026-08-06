import re
from datetime import datetime, timezone
from pathlib import Path

from agent.tools.tools_models import Tool, ToolResult


DEFAULT_MAX_PLAN_CHARS = 24_000
PLAN_SECTION_HEADER_RE = re.compile(r"^##\s+", re.MULTILINE)


def _resolve_workspace_file(workspace: Path, filename: str) -> Path:
    workspace_path = Path(workspace).resolve()
    target_path = (workspace_path / filename).resolve()
    if workspace_path != target_path and workspace_path not in target_path.parents:
        raise ValueError("Filename must stay inside the workspace")
    return target_path


def _extract_latest_execution_plan(content: str) -> str:
    marker = "# Execution Plan"
    marker_index = content.rfind(marker)
    if marker_index == -1:
        return content
    return content[marker_index:].strip()


def _append_section(base_content: str, section: str) -> str:
    sanitized = base_content.rstrip()
    if not sanitized:
        return section.strip() + "\n"
    return f"{sanitized}\n\n{section.strip()}\n"


def _replace_section(base_content: str, section_heading: str, section_content: str) -> str:
    if not section_heading.startswith("## "):
        raise ValueError("section_heading must start with '## '")

    start = base_content.find(section_heading)
    if start == -1:
        return _append_section(base_content, f"{section_heading}\n{section_content.strip()}")

    next_match = PLAN_SECTION_HEADER_RE.search(base_content, pos=start + len(section_heading))
    end = next_match.start() if next_match else len(base_content)

    replacement = f"{section_heading}\n{section_content.strip()}\n"
    updated = f"{base_content[:start].rstrip()}\n\n{replacement}\n{base_content[end:].lstrip()}"
    return updated.rstrip() + "\n"


def _enforce_plan_size(content: str, max_chars: int) -> str:
    if len(content) <= max_chars:
        return content
    raise ValueError(
        f"Plan too large ({len(content)} chars). Keep it under {max_chars} chars by summarizing older evidence and keeping only active steps."
    )


def _archive_current_plan(plan_path: Path, archive_dir: Path) -> Path | None:
    if not plan_path.exists():
        return None

    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = archive_dir / f"{plan_path.stem}_{timestamp}.md"
    archive_path.write_text(plan_path.read_text(encoding="utf-8"), encoding="utf-8")
    return archive_path



def read_plan_executor(workspace: Path, filename: str) -> ToolResult:
    max_chars = DEFAULT_MAX_PLAN_CHARS
    try:
        file_path = _resolve_workspace_file(Path(workspace), filename)
        content = file_path.read_text(encoding="utf-8")

        if len(content) > max_chars:
            metadata = {
                "truncated": True,
                "file": str(file_path),
                "total_chars": len(content),
                "max_chars": max_chars,
            }
            content = content[:max_chars] + "\n\n[TRUNCATED]"
        else:
            metadata = {
                "truncated": False,
                "file": str(file_path),
                "total_chars": len(content),
            }

        return ToolResult(
            ok=True,
            output=content,
            error=None,
            metadata=metadata,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            output=None,
            error=str(e),
            metadata={},
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
        content: str,
        mode: str = "replace",
        section_heading: str | None = None,
        max_chars: int = DEFAULT_MAX_PLAN_CHARS,
        archive_previous: bool = True,
) -> ToolResult:

    file_path = _resolve_workspace_file(Path(workspace), filename)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path = None

    
    if action == "create":
        try:
            if not file_path.exists():
                normalized = _extract_latest_execution_plan(content).strip() + "\n"
                normalized = _enforce_plan_size(normalized, max_chars=max_chars)
                file_path.write_text(normalized, encoding="utf-8")
                return ToolResult(
                    ok=True,
                    output="Plan successfully created.",
                    error=None,
                    metadata={
                        "file": str(file_path),
                        "mode": "replace",
                        "chars": len(normalized),
                    },
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
                existing = file_path.read_text(encoding="utf-8")

                if mode == "replace":
                    updated = _extract_latest_execution_plan(content).strip() + "\n"
                elif mode == "append":
                    updated = _append_section(existing, content)
                elif mode == "replace_section":
                    if not section_heading:
                        raise ValueError("section_heading is required for mode='replace_section'")
                    updated = _replace_section(existing, section_heading=section_heading, section_content=content)
                else:
                    raise ValueError("mode must be one of: replace, append, replace_section")

                updated = _enforce_plan_size(updated, max_chars=max_chars)

                if archive_previous and existing != updated:
                    archive_dir = file_path.parent / "plan" / "archive"
                    archive_path = _archive_current_plan(file_path, archive_dir)

                file_path.write_text(updated, encoding="utf-8")

                metadata = {
                    "file": str(file_path),
                    "mode": mode,
                    "chars": len(updated),
                }
                if archive_path is not None:
                    metadata["archived_to"] = str(archive_path)

                return ToolResult(
                    ok=True,
                    output="Plan successfully updated.",
                    error=None,
                    metadata=metadata,
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
                error="Plan does not exist, use `create` action first!",
                metadata={}
            )

CREATE_OR_UPDATE_PLAN_TOOL = Tool(
    name="create_or_update_plan",
    description=(
        "Create or update the active plan file. "
        "Use mode='replace' for full-plan rewrites, "
        "or mode='replace_section' for targeted updates."
    ),
    parameters={
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Plan filename, usually PLAN.md.",
            },
            "action": {
                "type": "string",
                "enum": ["create", "update"],
            },
            "content": {
                "type": "string",
            },
            "mode": {
                "type": "string",
                "enum": ["replace", "append", "replace_section"],
                "description": (
                    "Use 'replace' by default. "
                    "For action='create', use 'replace'."
                ),
            },
            "section_heading": {
                "type": ["string", "null"],
                "description": (
                    "Section heading when mode='replace_section', "
                    "otherwise null. Example: '## Step Tracker'."
                ),
            },
        },
        "required": [
            "filename",
            "action",
            "content",
            "mode",
            "section_heading",
        ],
        "additionalProperties": False,
    },
    executor=create_or_update_plan_executor,
)