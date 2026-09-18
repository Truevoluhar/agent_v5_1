"""Opt-in live integration check using a synthetic ZIP and the durable task board.

Usage: python scripts/live_smoke.py --config agent/config.yml --files 20
This makes billable calls to the configured provider; never runs during unit tests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.runner import AgentRunner, RunRequest
from agent.work_queue import TaskBoard


def _build_fixture(workspace: Path, files: int) -> list[str]:
    expected_paths: list[str] = []
    with zipfile.ZipFile(workspace / "source_bundle.zip", "w") as archive:
        for idx in range(files):
            group = f"PROJ{idx % 4:02d}"
            module = f"{group}__MODULE_{idx:02d}"
            archive.writestr(
                f"{module}.py",
                (
                    f"def compute_{idx}(value: int) -> int:\n"
                    f"    \"\"\"Return value plus {idx}.\"\"\"\n"
                    f"    return value + {idx}\n"
                ),
            )
            expected_paths.append(f"{group}/{group}_MODULE_{idx:02d}/README.md")
    (workspace / "TEMPLATE_README.md").write_text(
        (
            "# {{entity_name}}\n\n"
            "## Summary\n\n"
            "## Behavior\n\n"
            "## Inputs\n\n"
            "## Outputs\n\n"
            "## Example\n\n"
            "## Notes\n"
        ),
        encoding="utf-8",
    )
    return expected_paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="agent/config.yml")
    parser.add_argument("--files", type=int, default=20)
    parser.add_argument("--embedding-cache", help="Optional writable Chroma model cache")
    args = parser.parse_args()
    if not 1 <= args.files <= 20:
        parser.error("--files must be between 1 and 20 for this bounded smoke test")
    if args.embedding_cache:
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

        ONNXMiniLM_L6_V2.DOWNLOAD_PATH = Path(args.embedding_cache)
    root = Path(tempfile.mkdtemp(prefix="agent-live-smoke-"))
    workspace = root / "workspace"
    workspace.mkdir()
    expected_paths = _build_fixture(workspace, args.files)
    runner = AgentRunner(args.config)
    runner.config.update(
        session=str(root / "sessions"),
        memory=str(root / "memory"),
        agents_resources=str(Path(__file__).resolve().parents[1] / "data/resources/agents"),
        max_steps=48,
        max_worker_iterations=35,
    )
    runner.config["llm"] = {**runner.config.get("llm", {}), "timeout": 180, "max_retries": 1}
    started = time.monotonic()
    events: list[str] = []

    def emit(event):
        events.append(event.type)
        print("EVENT", event.type, flush=True)

    def no_input(question: str) -> str:
        raise RuntimeError(f"Smoke test unexpectedly requested user input: {question}")

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "readme_count": {"type": "integer"},
            "artifacts": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "readme_count", "artifacts"],
    }
    prompt = (
        f"In this workspace there is a zip file named source_bundle.zip containing exactly {args.files} Python files. "
        "Read and analyze every source file and create a comprehensive README.md for each one. "
        "Each README must follow TEMPLATE_README.md and must be written into a folder named after the project it refers to. "
        "Use the SQLite task board as the source of truth, break collection work into extract, inventory, and per-file tasks, "
        "prefer workspace_fs and task_board over run_shell, and keep artifacts in project-specific folders. "
        "Do not use PLAN.md."
    )
    result = runner.run(
        RunRequest(
            username="live_smoke",
            workspace=str(workspace),
            response_schema=json.dumps(schema),
            prompt=prompt,
        ),
        emit=emit,
        wait_for_input=no_input,
        is_cancelled=lambda: time.monotonic() - started > 1200,
    )
    state = TaskBoard(workspace, result.session_id).verify()
    artifacts = sorted(workspace.rglob("README.md"))
    expected_existing = [path for path in expected_paths if (workspace / path).is_file()]
    passed = (
        result.status == "completed"
        and state["remaining"] == 0
        and len(artifacts) == args.files
        and len(expected_existing) == args.files
        and result.final_response is not None
        and result.final_response.readme_count == args.files
        and set(expected_paths).issubset(set(result.final_response.artifacts))
        and "tool.completed" in events
    )
    report = {
        "passed": passed,
        "status": result.status,
        "error": result.error,
        "model": runner.config["orchestrator_agent"]["model"],
        "api_mode": runner.config.get("llm", {}).get("api_mode", "chat_completions"),
        "coverage": state,
        "artifact_count": len(artifacts),
        "expected_paths": expected_paths,
        "workspace": str(workspace),
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "final_response": result.final_response.model_dump() if result.final_response else None,
    }
    (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
