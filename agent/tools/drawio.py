from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from agent.tools.tools_models import Tool, ToolResult


REFERENCE_RELATIVE_PATH = Path("resources/file_resources/xml-reference.md")
DEFAULT_REFERENCE_MAX_CHARS = 12_000

HTML_TAG_RE = re.compile(r"<[^>]+>")
FORBIDDEN_EDGE_KEYS = ("exitX=", "exitY=", "entryX=", "entryY=")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _reference_path() -> Path:
    return _project_root() / REFERENCE_RELATIVE_PATH


def _resolve_workspace_file(workspace: Path, file_path: str) -> Path:
    workspace_path = Path(workspace).resolve()
    target_path = (workspace_path / file_path).resolve()

    if workspace_path != target_path and workspace_path not in target_path.parents:
        raise ValueError("Path must stay inside the workspace")

    return target_path


def _has_html_markup(value: str | None) -> bool:
    if not value:
        return False
    return bool(HTML_TAG_RE.search(value))


def _style_contains_html_enabled(style: str | None) -> bool:
    if not style:
        return False
    return "html=1" in style


def _validate_drawio_xml(xml_content: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if "<!--" in xml_content or "-->" in xml_content:
        errors.append("XML comments are forbidden in draw.io output.")

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return [f"XML is not well-formed: {exc}"], []

    if root.tag not in {"mxfile", "mxGraphModel"}:
        errors.append("Root element must be either <mxfile> or <mxGraphModel>.")

    if root.tag == "mxfile" and not any(node.tag == "mxGraphModel" for node in root.iter()):
        errors.append("mxfile must contain at least one mxGraphModel element.")

    seen_ids: set[str] = set()
    duplicate_ids: list[str] = []
    for node in root.iter():
        node_id = node.attrib.get("id")
        if not node_id:
            continue
        if node_id in seen_ids:
            duplicate_ids.append(node_id)
        else:
            seen_ids.add(node_id)

    if duplicate_ids:
        errors.append(f"Found duplicate id values: {', '.join(sorted(set(duplicate_ids)))}")

    for node in root.iter("Array"):
        if node.attrib.get("as") == "points":
            errors.append("Do not include <Array as=\"points\"> waypoints; use automatic routing.")
            break

    for cell in root.iter("mxCell"):
        style = cell.attrib.get("style", "")

        if cell.attrib.get("edge") == "1":
            geometry_children = [
                child
                for child in list(cell)
                if child.tag == "mxGeometry"
                and child.attrib.get("relative") == "1"
                and child.attrib.get("as") == "geometry"
            ]

            if not geometry_children:
                cell_id = cell.attrib.get("id", "<unknown>")
                errors.append(
                    f"Edge mxCell id={cell_id} must contain <mxGeometry relative=\"1\" as=\"geometry\"/>."
                )

            if any(key in style for key in FORBIDDEN_EDGE_KEYS):
                cell_id = cell.attrib.get("id", "<unknown>")
                warnings.append(
                    f"Edge id={cell_id} sets entry/exit connection overrides; avoid unless geometrically required."
                )

        value = cell.attrib.get("value")
        if _has_html_markup(value) and not _style_contains_html_enabled(style):
            cell_id = cell.attrib.get("id", "<unknown>")
            errors.append(f"Cell id={cell_id} uses HTML labels but style is missing html=1.")

    for obj in root.iter("object"):
        label = obj.attrib.get("label")
        inner_cell = next((child for child in list(obj) if child.tag == "mxCell"), None)
        inner_style = inner_cell.attrib.get("style", "") if inner_cell is not None else ""

        if _has_html_markup(label) and not _style_contains_html_enabled(inner_style):
            obj_id = obj.attrib.get("id", "<unknown>")
            errors.append(f"Object id={obj_id} uses HTML label but inner mxCell style is missing html=1.")

    return errors, warnings


def read_drawio_reference_executor(
    workspace: Path,
    max_chars: int = DEFAULT_REFERENCE_MAX_CHARS,
) -> ToolResult:
    try:
        reference = _reference_path()
        if not reference.exists():
            return ToolResult(
                ok=False,
                output=None,
                error=f"Reference file not found: {reference}",
                metadata={},
            )

        content = reference.read_text(encoding="utf-8")
        truncated = False

        if max_chars > 0 and len(content) > max_chars:
            content = content[:max_chars] + "\n\n[TRUNCATED]"
            truncated = True

        return ToolResult(
            ok=True,
            output=content,
            error=None,
            metadata={
                "reference_file": str(reference),
                "truncated": truncated,
                "max_chars": max_chars,
            },
        )
    except Exception as exc:
        return ToolResult(ok=False, output=None, error=str(exc), metadata={})


def upsert_drawio_diagram_executor(
    workspace: Path,
    diagram_path: str,
    action: str,
    xml_content: str,
    create_backup: bool,
) -> ToolResult:
    try:
        target = _resolve_workspace_file(Path(workspace), diagram_path)

        if target.suffix.lower() not in {".drawio", ".xml"}:
            return ToolResult(
                ok=False,
                output=None,
                error="Diagram file must end with .drawio or .xml",
                metadata={},
            )

        if action not in {"create", "update", "validate"}:
            return ToolResult(
                ok=False,
                output=None,
                error="action must be one of: create, update, validate",
                metadata={},
            )

        if action == "create" and target.exists():
            return ToolResult(
                ok=False,
                output=None,
                error="Diagram already exists. Use action='update' or 'validate'.",
                metadata={},
            )

        if action in {"update", "validate"} and not xml_content.strip():
            if target.exists():
                xml_content = target.read_text(encoding="utf-8")
            else:
                return ToolResult(
                    ok=False,
                    output=None,
                    error="xml_content is required when the target file does not exist.",
                    metadata={},
                )

        if action == "update" and not target.exists():
            return ToolResult(
                ok=False,
                output=None,
                error="Diagram does not exist. Use action='create' first.",
                metadata={},
            )

        errors, warnings = _validate_drawio_xml(xml_content)

        if errors:
            return ToolResult(
                ok=False,
                output="\n".join(errors),
                error="Draw.io XML validation failed.",
                metadata={
                    "diagram_file": str(target),
                    "validation_errors": errors,
                    "validation_warnings": warnings,
                },
            )

        backup_path = None
        if action == "update" and create_backup and target.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = target.with_suffix(target.suffix + f".{timestamp}.bak")
            backup_path.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")

        if action in {"create", "update"}:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(xml_content.strip() + "\n", encoding="utf-8")

            return ToolResult(
                ok=True,
                output=f"Diagram {action}d successfully.",
                error=None,
                metadata={
                    "diagram_file": str(target),
                    "action": action,
                    "chars": len(xml_content),
                    "backup_file": str(backup_path) if backup_path else None,
                    "validation_warnings": warnings,
                    "reference_file": str(_reference_path()),
                },
            )

        # validate-only
        return ToolResult(
            ok=True,
            output="Draw.io XML is valid according to enforced reference rules.",
            error=None,
            metadata={
                "diagram_file": str(target),
                "action": action,
                "validation_warnings": warnings,
                "reference_file": str(_reference_path()),
            },
        )

    except Exception as exc:
        return ToolResult(ok=False, output=None, error=str(exc), metadata={})


READ_DRAWIO_REFERENCE_TOOL = Tool(
    name="read_drawio_reference",
    description=(
        "Read draw.io XML rules from resources/file_resources/xml-reference.md. "
        "Use this before creating or modifying draw.io diagrams."
    ),
    parameters={
        "type": "object",
        "properties": {
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return. Use 0 for full file.",
                "default": DEFAULT_REFERENCE_MAX_CHARS,
            }
        },
        "required": ["max_chars"],
        "additionalProperties": False,
    },
    executor=read_drawio_reference_executor,
)


UPSERT_DRAWIO_DIAGRAM_TOOL = Tool(
    name="upsert_drawio_diagram",
    description=(
        "Create, update, or validate a draw.io XML diagram inside the workspace. "
        "Enforces critical rules from xml-reference.md (well-formed XML, no comments, "
        "valid edge geometry, no manual waypoint arrays, unique IDs, and html=1 for HTML labels)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "diagram_path": {
                "type": "string",
                "description": "Path inside workspace, e.g. diagrams/system.drawio",
            },
            "action": {
                "type": "string",
                "enum": ["create", "update", "validate"],
            },
            "xml_content": {
                "type": "string",
                "description": "Full draw.io XML content. For validate/update you may pass an empty string to validate the current file.",
            },
            "create_backup": {
                "type": "boolean",
                "description": "When updating, create a timestamped .bak file first.",
                "default": True,
            },
        },
        "required": ["diagram_path", "action", "xml_content", "create_backup"],
        "additionalProperties": False,
    },
    executor=upsert_drawio_diagram_executor,
)
