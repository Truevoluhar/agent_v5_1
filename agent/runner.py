"""Reusable, in-process agent execution loop."""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Optional

from dotenv import load_dotenv
import yaml

from agent.events import EventEmitter, EventSink
from agent.execution import BudgetExhausted, EXECUTION_POLICY, RunCancelled, workspace_lock
from agent.generic_agent import GenericAgent
from agent.llm import safe_endpoint, safe_exception_summary
from agent.orchestrator_agent import OrchestratorAgent
from agent.paths import DATA_ROOT
from agent.response_agent import ResponseAgent
from agent.session import Session
from agent.user_storage import user_storage_paths
from agent.work_queue import TaskBoard, read_sample, workspace_file

AGENT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = str(AGENT_ROOT / "config.yml")

WaitForInput = Callable[[str], str]
IsCancelled = Callable[[], bool]
logger = logging.getLogger(__name__)


class IncompleteRun(BudgetExhausted):
    def __init__(self, message: str, final_response: Any = None):
        super().__init__(message)
        self.final_response = final_response


@dataclass
class RunRequest:
    username: str
    prompt: str
    workspace: Optional[str] = None
    session_id: Optional[str] = None
    run_id: Optional[str] = None
    response_schema: Optional[str] = None
    max_context_chars: Optional[int] = None


@dataclass
class RunResult:
    run_id: str
    session_id: str
    status: str
    final_response: Any = None
    error: Optional[str] = None


def _find_agent_by_name(agents: list[GenericAgent], agent_name: str) -> GenericAgent | None:
    for agent in agents:
        if agent.name == agent_name:
            return agent
    return None


def _looks_like_placeholder_instruction(text: str) -> bool:
    normalized = " ".join(str(text or "").strip().lower().split())
    if not normalized:
        return True
    if len(normalized) < 24:
        return True
    placeholders = {
        "delegate next task",
        "do the work",
        "continue",
        "resume",
        "handle it",
        "work on it",
        "next task",
    }
    return normalized in placeholders


def _build_delegation_instructions(task: dict[str, Any], description: str) -> str:
    cleaned_description = " ".join(str(description or "").split())
    instructions: list[str] = []
    metadata = task.get("task_metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    if cleaned_description and not _looks_like_placeholder_instruction(cleaned_description):
        instructions.append(cleaned_description)
    else:
        instructions.append(f"Complete task {task['task_key']}: {task['title']}.")
    if task.get("source_path"):
        instructions.append(f"Analyze source file '{task['source_path']}'.")
    reference_paths = [str(item).strip() for item in (metadata.get("reference_paths") or []) if str(item).strip()]
    if reference_paths:
        instructions.append("Use reference file(s): " + ", ".join(f"'{item}'" for item in reference_paths[:4]) + ".")
    if metadata.get("entity_name"):
        instructions.append(f"Primary work item name: '{metadata['entity_name']}'.")
    if metadata.get("group_name"):
        instructions.append(f"Group or project key: '{metadata['group_name']}'.")
    if metadata.get("target_dir"):
        instructions.append(f"Create or update the target directory '{metadata['target_dir']}'.")
    if metadata.get("target_path"):
        instructions.append(f"Write the final artifact exactly to '{metadata['target_path']}'.")
    if task.get("description"):
        instructions.append(str(task["description"]).strip())
    acceptance = [item.strip() for item in (task.get("acceptance_criteria") or []) if str(item).strip()]
    if acceptance:
        instructions.append("Acceptance criteria: " + "; ".join(acceptance))
    instructions.append(
        "Save files before reporting, then call task_board(action='submit') with exact artifact paths. "
        "If completion is impossible, call task_board(action='block') with the real blocker."
    )
    return " ".join(part for part in instructions if part)


def _recommended_step_budget(base_max_steps: int, board_summary: dict[str, Any]) -> int:
    counts = dict(board_summary.get("counts") or {})
    remaining = int(board_summary.get("remaining") or 0)
    review_queue = int(counts.get("reported", 0)) + int(counts.get("blocked", 0))
    active = int(counts.get("in_progress", 0))
    if remaining <= 0:
        return base_max_steps
    # A successful task typically needs one delegation step and one review step.
    recommended = (remaining * 2) + review_queue + active + 4
    return max(base_max_steps, recommended)


def _looks_like_collection_wide_task(task: dict[str, Any]) -> bool:
    metadata = task.get("task_metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    if task.get("source_path"):
        return False
    if metadata.get("target_path"):
        return False
    haystack = " ".join(
        str(part or "")
        for part in [
            task.get("task_key"),
            task.get("title"),
            task.get("description"),
            " ".join(str(item) for item in (task.get("acceptance_criteria") or [])),
        ]
    ).lower()
    markers = (
        "each file",
        "every file",
        "all files",
        "per file",
        "each document",
        "every document",
        "all documents",
        "for each extracted file",
    )
    return any(marker in haystack for marker in markers)


def _has_bootstrap_backlog(board: TaskBoard, current_task_id: int | None = None) -> bool:
    open_tasks = board.list_tasks(statuses=["ready", "pending"], limit=200)
    for item in open_tasks:
        if current_task_id is not None and int(item.get("id") or 0) == int(current_task_id):
            continue
        haystack = " ".join(
            str(part or "")
            for part in [item.get("task_key"), item.get("title"), item.get("description")]
        ).lower()
        if any(marker in haystack for marker in ("inventory", "seed", "inspect", "enumerate", "list all")):
            return True
    return False


def _has_open_file_backlog(board: TaskBoard, current_task_id: int | None = None) -> bool:
    open_tasks = board.list_tasks(statuses=["ready", "pending", "in_progress", "reported", "blocked"], limit=500)
    for item in open_tasks:
        if current_task_id is not None and int(item.get("id") or 0) == int(current_task_id):
            continue
        if item.get("source_path"):
            return True
    return False


def _requires_bootstrap_before_dispatch(board: TaskBoard, task: dict[str, Any]) -> bool:
    if not _looks_like_collection_wide_task(task):
        return False
    current_task_id = int(task.get("id") or 0)
    return _has_bootstrap_backlog(board, current_task_id=current_task_id) or _has_open_file_backlog(
        board, current_task_id=current_task_id
    )


def _prompt_implies_collection_work(objective: str) -> bool:
    text = str(objective or "").lower()
    markers = (
        "every file",
        "each file",
        "all files",
        "every document",
        "each document",
        "all documents",
        "zip",
        "archive",
        "readme for each",
        "for each file",
    )
    return any(marker in text for marker in markers)


def _runtime_task_key(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "").upper())
    cleaned = cleaned.strip("-")
    return cleaned or "TASK"


def _detect_workspace_snapshot(workspace: str) -> dict[str, Any]:
    root = Path(workspace)
    archives: list[str] = []
    candidate_dirs: list[str] = []
    text_files = 0
    for path in sorted(root.rglob("*")):
        if any(part in {".agent", ".git", "node_modules", "venv", "__pycache__"} for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            if path.suffix.lower() == ".zip":
                archives.append(relative)
            else:
                try:
                    sample = read_sample(path, 4096)
                except OSError:
                    continue
                if TaskBoard._detect_text_encoding(sample) is not None:
                    text_files += 1
        elif path.is_dir() and path.name.lower() in {"src", "source", "sources", "extracted", "extracted_docs", "documents"}:
            candidate_dirs.append(relative)
    return {
        "archives": archives,
        "candidate_dirs": candidate_dirs,
        "text_files": text_files,
    }


def _auto_submit_completed_artifact_task(
    board: TaskBoard,
    task: dict[str, Any] | None,
    agent_name: str,
) -> dict[str, Any] | None:
    if not task or task.get("status") != "in_progress":
        return task
    if not task.get("source_path"):
        return task
    metadata = task.get("task_metadata") or {}
    if not isinstance(metadata, dict):
        return task
    target_path = str(metadata.get("target_path") or "").strip()
    if not target_path:
        return task
    source_path = workspace_file(board.root, str(task["source_path"]))
    artifact_path = workspace_file(board.root, target_path)
    if not source_path.is_file() or not artifact_path.is_file():
        return task
    if int(task.get("source_cursor") or 0) < source_path.stat().st_size:
        return task
    try:
        preview = artifact_path.read_text(encoding="utf-8", errors="replace")[:240]
        board.submit(
            int(task["id"]),
            summary=f"Created {target_path} for {Path(task['source_path']).name}.",
            evidence=(
                f"Recovered worker output automatically because the artifact already existed. "
                f"Fully read '{task['source_path']}' and found '{target_path}'. Preview: {preview}"
            ),
            artifacts=[target_path],
            agent_name=agent_name,
        )
    except Exception:
        return task
    return board.get_task(task_id=int(task["id"]))


def _auto_submit_seed_task(
    board: TaskBoard,
    task: dict[str, Any] | None,
    agent_name: str,
) -> dict[str, Any] | None:
    if not task or task.get("status") != "in_progress" or task.get("source_path"):
        return task
    haystack = " ".join(
        str(task.get(field) or "") for field in ("task_key", "title", "description")
    ).lower()
    if not any(marker in haystack for marker in ("inventory", "seed")):
        return task
    file_tasks = [
        item
        for item in board.list_tasks(
            statuses=["ready", "pending", "in_progress", "reported", "blocked", "validated"],
            limit=1000,
        )
        if item.get("source_path")
    ]
    if not file_tasks:
        return task
    try:
        board.submit(
            int(task["id"]),
            summary=f"Seeded {len(file_tasks)} durable file tasks.",
            evidence=(
                f"Recovered worker output automatically because inventory results already exist in the task board. "
                f"Found {len(file_tasks)} file-backed tasks after inventory/seeding work."
            ),
            artifacts=[],
            agent_name=agent_name,
        )
    except Exception:
        return task
    return board.get_task(task_id=int(task["id"]))


def _cleanup_redundant_collection_tasks(board: TaskBoard) -> int:
    tasks = board.list_tasks(statuses=["ready", "pending", "blocked"], limit=1000)
    file_tasks = [item for item in tasks if item.get("source_path")]
    if not file_tasks:
        return 0
    cancelled = 0
    for task in tasks:
        if task.get("source_path"):
            continue
        haystack = " ".join(
            str(task.get(field) or "") for field in ("task_key", "title", "description")
        ).lower()
        if any(marker in haystack for marker in ("inventory", "seed")):
            board.cancel(
                int(task["id"]),
                "Redundant coordination task cancelled because durable file tasks already exist.",
            )
            cancelled += 1
            continue
        if _looks_like_collection_wide_task(task):
            board.cancel(
                int(task["id"]),
                "Broad collection task cancelled because the work has been expanded into durable file tasks.",
            )
            cancelled += 1
    return cancelled


def _fallback_orchestrator_decision(
    *,
    ready_tasks: list[dict[str, Any]],
    agents: list[GenericAgent],
    error: Exception,
) -> SimpleNamespace:
    if not ready_tasks:
        raise error
    task = ready_tasks[0]
    preferred_agent = _find_agent_by_name(agents, str(task.get("suggested_agent") or ""))
    delegated_agent = preferred_agent or (agents[0] if agents else None)
    if delegated_agent is None:
        raise error
    description = (
        "Fallback delegation because the orchestrator returned an invalid decision. "
        f"Complete task {task['task_key']}: {task['title']}."
    )
    return SimpleNamespace(
        action="delegate_to_agent",
        description=description,
        task_key=task["task_key"],
        agent_name=delegated_agent.name,
    )


def _finalize_completed_work(
    *,
    board: TaskBoard,
    response_agent: ResponseAgent | None,
    session: Session,
    response_context_budget: int,
    response_schema_source: Any,
    emitter: EventEmitter,
    is_cancelled: IsCancelled,
    completion_note: str,
) -> tuple[bool, Any]:
    coverage = board.verify()
    emitter.emit("work.coverage", coverage)
    if coverage["remaining"]:
        return False, None

    if response_agent is not None:
        emitter.emit("response.started", {})
        final_messages = session.get_bounded_context(
            max_recent_messages=20,
            max_context_chars=response_context_budget,
        )
        final_messages.append(
            {
                "role": "user",
                "content": completion_note + "\n" + json.dumps(board.completion_report()),
            }
        )
        final_response = response_agent.chat_structured(
            messages=final_messages,
            schema_source=response_schema_source,
            session=session,
        )
        if is_cancelled():
            raise RunCancelled()
        return True, final_response

    return True, None


class AgentRunner:
    """Loads config once and executes runs against it."""

    def __init__(self, config_path: str | None = None):
        load_dotenv(AGENT_ROOT.parent / ".env", override=False)
        config_path = config_path or os.getenv("AGENT_CONFIG_PATH") or CONFIG_PATH
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def run(self, request, emit, wait_for_input, is_cancelled=None):
        workspace_value = request.workspace or self.config["workspace"]
        workspace = DATA_ROOT / workspace_value if workspace_value else DATA_ROOT
        with workspace_lock(workspace):
            return self._run(request, emit, wait_for_input, is_cancelled)

    def _run(
        self,
        request: RunRequest,
        emit: EventSink,
        wait_for_input: WaitForInput,
        is_cancelled: IsCancelled | None = None,
    ) -> RunResult:
        config = self.config
        is_cancelled = is_cancelled or (lambda: False)

        try:
            user_storage = user_storage_paths(
                request.username,
                session_folder=DATA_ROOT / config["session"],
                memory_folder=DATA_ROOT / config["memory"],
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        options = config.get("llm", {}) or {}
        agents_config = config["agents"]
        orchestrator_config = config["orchestrator_agent"]
        response_agent_config = config.get("response_agent")
        agent_resources = str(DATA_ROOT / config["agents_resources"])
        context_limits = dict(config.get("context_limits", {}) or {})

        if request.max_context_chars is not None:
            context_limits["max_input_chars"] = int(request.max_context_chars)

        max_input_chars = int(context_limits.get("max_input_chars", 120000))
        orchestrator_context_budget = max(4000, int(max_input_chars * 0.45))
        delegated_context_budget = max(4000, int(max_input_chars * 0.50))
        response_context_budget = max(6000, int(max_input_chars * 0.60))

        config_response_schema = config.get("response_schema_path", "resources/response_schema.json")
        response_schema_source = request.response_schema or config_response_schema
        if isinstance(response_schema_source, str):
            raw_schema = response_schema_source.strip()
            if raw_schema.startswith("{") or raw_schema.startswith("["):
                response_schema_source = raw_schema
            else:
                response_schema_source = str(DATA_ROOT / raw_schema)

        workspace_value = request.workspace or config["workspace"]
        agent_workspace = str(DATA_ROOT / workspace_value) if workspace_value else str(DATA_ROOT)
        Path(agent_workspace).mkdir(parents=True, exist_ok=True)

        session = Session(
            id=request.session_id,
            session_folder=user_storage.session_folder,
            workspace_folder=agent_workspace,
            memory_folder=user_storage.memory_folder,
        )
        if session.is_new:
            session.set_name(self._generate_session_name(request.prompt))

        run_id = request.run_id or session.id
        emitter = EventEmitter(run_id=run_id, session_id=session.id, sink=emit)
        emitter.emit("run.started", {"username": request.username, "workspace": agent_workspace})

        agents: list[GenericAgent] = []
        for agent_id, agent_data in agents_config.items():
            agents.append(
                GenericAgent(
                    id=agent_id,
                    name=agent_data["name"],
                    model=agent_data["model"],
                    temperature=agent_data["temperature"],
                    base_url=agent_data["base_url"],
                    api_key=os.getenv(agent_data["api_key"]),
                    resources_path=agent_resources,
                    workspace_path=agent_workspace,
                    context_limits=context_limits,
                    llm_options={**options, **agent_data.get("llm", {})},
                )
            )

        orchestrator_agent = OrchestratorAgent(
            id="orchestrator_agent",
            name=orchestrator_config["name"],
            model=orchestrator_config["model"],
            temperature=orchestrator_config["temperature"],
            base_url=orchestrator_config["base_url"],
            api_key=os.getenv(orchestrator_config["api_key"]),
            resources_path=agent_resources,
            workspace_path=agent_workspace,
            available_agents=[agent.name for agent in agents],
            context_limits=context_limits,
            llm_options={**options, **orchestrator_config.get("llm", {})},
        )

        response_agent = None
        if response_agent_config:
            response_agent = ResponseAgent(
                id="response_agent",
                name=response_agent_config["name"],
                model=response_agent_config["model"],
                temperature=response_agent_config["temperature"],
                base_url=response_agent_config["base_url"],
                api_key=os.getenv(response_agent_config["api_key"]),
                resources_path=agent_resources,
                workspace_path=agent_workspace,
                response_schema_source=response_schema_source,
                context_limits=context_limits,
                llm_options={**options, **response_agent_config.get("llm", {})},
            )

        session.add_message({"role": "user", "content": request.prompt})

        try:
            final_response = self._run_loop(
                session=session,
                config=config,
                agents=agents,
                orchestrator_agent=orchestrator_agent,
                response_agent=response_agent,
                agent_workspace=agent_workspace,
                orchestrator_context_budget=orchestrator_context_budget,
                delegated_context_budget=delegated_context_budget,
                response_context_budget=response_context_budget,
                response_schema_source=response_schema_source,
                emitter=emitter,
                wait_for_input=wait_for_input,
                is_cancelled=is_cancelled,
            )
        except IncompleteRun as exc:
            emitter.emit("run.failed", {"error": str(exc), "resumable": True})
            return RunResult(
                run_id=run_id,
                session_id=session.id,
                status="failed",
                error=str(exc),
                final_response=exc.final_response,
            )
        except BudgetExhausted as exc:
            emitter.emit("run.failed", {"error": str(exc), "resumable": True})
            return RunResult(run_id=run_id, session_id=session.id, status="failed", error=str(exc))
        except RunCancelled:
            emitter.emit("run.cancelled", {})
            return RunResult(run_id=run_id, session_id=session.id, status="cancelled")
        except Exception as exc:
            error = safe_exception_summary(exc)
            logger.exception(
                "Agent run failed run_id=%s session_id=%s endpoint=%s model=%s error=%s",
                run_id,
                session.id,
                safe_endpoint(orchestrator_config.get("base_url")),
                orchestrator_config.get("model", "unconfigured"),
                error,
            )
            emitter.emit("run.failed", {"error": error})
            return RunResult(run_id=run_id, session_id=session.id, status="failed", error=error)

        emitter.emit("run.completed", {})
        return RunResult(run_id=run_id, session_id=session.id, status="completed", final_response=final_response)

    @staticmethod
    def _generate_session_name(prompt: str) -> str:
        plain_text = re.sub(r"[`#*_>\[\]{}()]", " ", str(prompt or ""))
        words = plain_text.split()
        if not words:
            return "New chat"
        return " ".join(words[:8])[:120]

    def _build_retrieval_context(self, session: Session, query: str, budget: int) -> str:
        retrieval_limit = Session.suggest_retrieval_limit(
            context_budget_chars=max(600, budget // 5),
            min_limit=1,
            max_limit=6,
            chars_per_match=450,
        )
        return session.format_retrieval_context(
            query=query,
            limit=retrieval_limit,
            max_chars=max(600, budget // 4),
        )

    def _ensure_tasks_planned(
        self,
        *,
        board: TaskBoard,
        session: Session,
        objective: str,
        orchestrator_agent: OrchestratorAgent,
        emitter: EventEmitter,
        context_budget: int,
    ) -> None:
        if board.has_tasks():
            return

        planning_messages = session.get_bounded_context(
            max_recent_messages=12,
            max_context_chars=context_budget,
        )
        retrieval_context = self._build_retrieval_context(session, objective, context_budget)
        if retrieval_context:
            planning_messages.insert(0, {"role": "system", "content": retrieval_context})
        workspace_snapshot = _detect_workspace_snapshot(str(board.root))
        planning_messages.append(
            {
                "role": "user",
                "content": (
                    "Create the initial SQLite task board for this user request. "
                    "Break the work into concrete tasks with dependencies, priorities, suggested agents, "
                    "and acceptance criteria. Use all available agents where it helps. "
                    "For work that depends on discovering files inside an archive or large directory, "
                    "prefer bootstrap tasks first: extract or inspect the collection, inventory it, "
                    "then create a follow-up task whose explicit job is to call "
                    "task_board(action='inventory') so the runtime can seed one durable file task per discovered file. "
                    "Do not guess or pre-create many file-specific tasks before the relevant files are actually known. "
                    "Current workspace snapshot:\n"
                    + json.dumps(workspace_snapshot, ensure_ascii=False)
                    + "\n"
                    "Current objective:\n" + objective
                ),
            }
        )
        emitter.emit("orchestrator.started", {"mode": "planning"})
        plan = orchestrator_agent.plan_tasks(planning_messages)
        planned_tasks = [task.model_dump(exclude_none=True) for task in plan.tasks]
        if not planned_tasks:
            planned_tasks = [
                {
                    "task_key": "TASK-PRIMARY",
                    "title": "Complete the user request",
                    "description": objective,
                    "task_type": "implementation",
                    "priority": 10,
                    "acceptance_criteria": ["The user request is completed and evidenced on disk or in tool output."],
                }
            ]
        created = board.add_tasks(planned_tasks, created_by=orchestrator_agent.name)
        session.add_message(
            {
                "role": "assistant",
                "content": (
                    f"Orchestrator created {len(created)} durable tasks. "
                    f"Planning summary: {plan.summary}"
                ),
            }
        )
        emitter.emit(
            "orchestrator.decision",
            {"action": "plan_tasks", "task_count": len(created), "description": plan.summary},
        )

    def _ensure_runtime_scaffold(
        self,
        *,
        board: TaskBoard,
        objective: str,
        agents: list[GenericAgent],
        agent_workspace: str,
        emitter: EventEmitter,
    ) -> None:
        if not _prompt_implies_collection_work(objective):
            return

        snapshot = _detect_workspace_snapshot(agent_workspace)
        preferred_agent = None
        for candidate in ("PROGRAMMER", "PLANNER"):
            preferred_agent = _find_agent_by_name(agents, candidate)
            if preferred_agent is not None:
                break
        if preferred_agent is None and agents:
            preferred_agent = agents[0]
        suggested_agent = preferred_agent.name if preferred_agent is not None else None

        existing = board.list_tasks(limit=500)
        existing_keys = {str(item.get("task_key") or "") for item in existing}
        source_tasks_exist = any(item.get("source_path") for item in existing)

        scaffold_tasks: list[dict[str, Any]] = []
        extract_keys: list[str] = []
        archive_roots: list[str] = []
        for archive in snapshot["archives"]:
            task_key = _runtime_task_key(f"EXTRACT-{Path(archive).stem}")
            extract_keys.append(task_key)
            archive_root = f"extracted/{Path(archive).stem}"
            archive_roots.append(archive_root)
            if task_key in existing_keys:
                continue
            scaffold_tasks.append(
                {
                    "task_key": task_key,
                    "title": f"Extract archive {archive}",
                    "description": (
                        f"Extract '{archive}' into '{archive_root}' using workspace_fs(action='extract_zip'). "
                        "Do not extract the same archive into multiple destinations."
                    ),
                    "task_type": "implementation",
                    "priority": 1,
                    "suggested_agent": suggested_agent,
                    "acceptance_criteria": [f"Archive extracted into {archive_root}"],
                    "task_metadata": [
                        {"key": "archive_path", "value": archive, "values": []},
                        {"key": "extract_destination", "value": archive_root, "values": []},
                    ],
                }
            )

        if scaffold_tasks:
            created = board.add_tasks(scaffold_tasks, created_by="runtime_scaffold")
            emitter.emit("orchestrator.decision", {"action": "runtime_scaffold", "task_count": len(created)})
            existing.extend(created)
            existing_keys.update(item["task_key"] for item in created)

        if source_tasks_exist:
            return

        roots = [item for item in snapshot["candidate_dirs"] if item]
        for archive_root in archive_roots:
            if archive_root not in roots:
                roots.append(archive_root)
        if not roots and snapshot["text_files"] > 0:
            roots = ["."]
        if not roots:
            return

        lower_objective = objective.lower()
        documentation_mode = "readme" in lower_objective or "template_readme" in lower_objective
        task_type = "documentation" if documentation_mode else "analysis"
        title_prefix = "Generate README for" if documentation_mode else "Analyze"
        acceptance = (
            ["README.md created", "README saved to target_path"]
            if documentation_mode
            else ["Source file analyzed and findings saved or reported"]
        )
        for root in roots:
            normalized_root = root.strip("./") or "workspace"
            task_key = _runtime_task_key(f"SEED-{normalized_root.replace('/', '-')}")
            if task_key in existing_keys:
                continue
            depends = [key for key in extract_keys if normalized_root.startswith("extracted") or root.startswith("extracted/")]
            description = (
                f"Inventory text-like files under '{root}' and create one durable file task per file with "
                "task_board(action='inventory'). Use include_binary=false and do not create duplicate source tasks."
            )
            if documentation_mode:
                description += " Keep derived target_dir and target_path metadata so workers can write README.md files in project-specific folders."
            created = board.add_tasks(
                [
                    {
                        "task_key": task_key,
                        "title": f"Seed file tasks from {root}",
                        "description": description,
                        "task_type": "coordination",
                        "priority": 2,
                        "depends_on_keys": depends,
                        "suggested_agent": suggested_agent,
                        "acceptance_criteria": acceptance,
                        "task_metadata": [
                            {"key": "inventory_root", "value": root, "values": []},
                            {"key": "inventory_pattern", "value": "**/*", "values": []},
                            {"key": "seed_task_type", "value": task_type, "values": []},
                            {"key": "seed_title_prefix", "value": title_prefix, "values": []},
                        ],
                    }
                ],
                created_by="runtime_scaffold",
            )
            if created:
                emitter.emit("orchestrator.decision", {"action": "runtime_scaffold", "task_count": len(created)})

    def _review_reported_task(
        self,
        *,
        board: TaskBoard,
        session: Session,
        objective: str,
        orchestrator_agent: OrchestratorAgent,
        emitter: EventEmitter,
        wait_for_input: WaitForInput,
        is_cancelled: IsCancelled,
        context_budget: int,
    ) -> None:
        review_task = board.list_tasks(statuses=["reported", "blocked"], limit=1)
        if not review_task:
            return
        task = review_task[0]
        review_messages = session.get_bounded_context(
            max_recent_messages=12,
            max_context_chars=context_budget,
        )
        review_messages.append(
            {
                "role": "user",
                "content": (
                    "Review this delegated task result and decide whether to accept it, "
                    "return it for rework, cancel it, or ask the user.\n"
                    "When the broader job involves archives or many files, prefer follow-up "
                    "inventory or per-file seeding tasks over a single collection-wide "
                    "implementation task.\n"
                    + json.dumps(
                        {
                            "objective": objective,
                            "task": task,
                            "board_summary": board.summary(),
                            "recent_activity": board.recent_activity(limit=8),
                        },
                        ensure_ascii=False,
                    )
                ),
            }
        )
        emitter.emit("orchestrator.started", {"mode": "review", "task_id": task["id"]})
        review = orchestrator_agent.review_task(review_messages)
        emitter.emit(
            "orchestrator.decision",
            {"action": "review_task", "task_id": task["id"], "outcome": review.outcome},
        )

        if review.outcome == "ask_user":
            emitter.emit("input.required", {"question": review.validation_notes})
            user_response = wait_for_input(review.validation_notes)
            if is_cancelled():
                raise RunCancelled()
            session.add_message({"role": "user", "content": user_response})
            board.reopen(task["id"], "User clarification requested before validation.")
            board.objective(user_response)
            return

        if getattr(review, "new_tasks", None):
            created = board.add_tasks(
                [item.model_dump(exclude_none=True) for item in review.new_tasks],
                created_by=orchestrator_agent.name,
            )
            if created:
                session.add_message(
                    {
                        "role": "assistant",
                        "content": f"Orchestrator created {len(created)} follow-up tasks during review.",
                    }
                )

        if review.outcome == "accept" and task["status"] != "reported":
            board.reopen(
                task["id"],
                "Task cannot be accepted while blocked; inspect the blocker, verify artifacts, and resubmit.",
            )
            session.add_message(
                {
                    "role": "assistant",
                    "content": (
                        f"Task {task['task_key']} was blocked, so acceptance was rejected and the task was reopened. "
                        "It needs a fresh worker report before validation."
                    ),
                }
            )
            return

        if review.outcome == "accept":
            board.validate(task["id"], accepted=True, validation_notes=review.validation_notes)
        elif review.outcome == "rework":
            if task["status"] == "reported":
                board.validate(task["id"], accepted=False, validation_notes=review.validation_notes)
            else:
                board.reopen(task["id"], review.validation_notes)
        elif review.outcome == "cancel":
            board.cancel(task["id"], review.validation_notes)

        session.add_message(
            {
                "role": "assistant",
                "content": f"Task {task['task_key']} review outcome: {review.outcome}. {review.validation_notes}",
            }
        )

    def _run_loop(
        self,
        *,
        session: Session,
        config: dict[str, Any],
        agents: list[GenericAgent],
        orchestrator_agent: OrchestratorAgent,
        response_agent: ResponseAgent | None,
        agent_workspace: str,
        orchestrator_context_budget: int,
        delegated_context_budget: int,
        response_context_budget: int,
        response_schema_source: Any,
        emitter: EventEmitter,
        wait_for_input: WaitForInput,
        is_cancelled: IsCancelled,
    ):
        board = TaskBoard(agent_workspace, session.id)
        objective = next(
            (m.get("content", "") for m in reversed(session.messages) if m.get("role") == "user"),
            "",
        )
        objective = board.objective(str(objective))

        step = 0
        max_steps = int(config["max_steps"])
        while step < max_steps:
            try:
                if is_cancelled():
                    raise RunCancelled()

                emitter.emit("step.started", {"step": step})
                self._ensure_tasks_planned(
                    board=board,
                    session=session,
                    objective=objective,
                    orchestrator_agent=orchestrator_agent,
                    emitter=emitter,
                    context_budget=orchestrator_context_budget,
                )
                self._ensure_runtime_scaffold(
                    board=board,
                    objective=objective,
                    agents=agents,
                    agent_workspace=agent_workspace,
                    emitter=emitter,
                )
                cleaned = _cleanup_redundant_collection_tasks(board)
                if cleaned:
                    emitter.emit("orchestrator.decision", {"action": "cleanup_redundant_tasks", "task_count": cleaned})
                max_steps = _recommended_step_budget(max_steps, board.summary())

                coverage = board.verify()
                emitter.emit("work.coverage", coverage)
                if coverage["remaining"] == 0 and board.has_tasks():
                    finalized, final_response = _finalize_completed_work(
                        board=board,
                        response_agent=response_agent,
                        session=session,
                        response_context_budget=response_context_budget,
                        response_schema_source=response_schema_source,
                        emitter=emitter,
                        is_cancelled=is_cancelled,
                        completion_note=(
                            "Summarize the completed work in the required JSON structure. "
                            "Use the validated task board report as evidence. "
                            "Never invent filenames or claim work was tested without evidence."
                        ),
                    )
                    if finalized:
                        return final_response

                if board.list_tasks(statuses=["reported", "blocked"], limit=1):
                    self._review_reported_task(
                        board=board,
                        session=session,
                        objective=objective,
                        orchestrator_agent=orchestrator_agent,
                        emitter=emitter,
                        wait_for_input=wait_for_input,
                        is_cancelled=is_cancelled,
                        context_budget=orchestrator_context_budget,
                    )
                    objective = board.objective("")
                    continue

                ready_tasks = board.list_tasks(statuses=["ready"], limit=6)
                if not ready_tasks:
                    session.add_message(
                        {
                            "role": "user",
                            "content": (
                                "No ready tasks are available, but the task board is not finished. "
                                "Resolve blocked tasks or ask the user for clarification."
                            ),
                        }
                    )
                    objective = board.objective("")
                    continue

                orchestration_messages = session.get_bounded_context(
                    max_recent_messages=12,
                    max_context_chars=orchestrator_context_budget,
                )
                retrieval_context = self._build_retrieval_context(session, objective, orchestrator_context_budget)
                if retrieval_context:
                    orchestration_messages.insert(0, {"role": "system", "content": retrieval_context})
                workspace_snapshot = _detect_workspace_snapshot(agent_workspace)
                orchestration_messages.append(
                    {
                        "role": "user",
                        "content": (
                            EXECUTION_POLICY
                            + "\nCurrent objective: "
                            + objective
                            + "\nTask board summary: "
                            + json.dumps(board.summary(), ensure_ascii=False)
                            + "\nWorkspace snapshot: "
                            + json.dumps(workspace_snapshot, ensure_ascii=False)
                            + "\nReady tasks: "
                            + json.dumps(ready_tasks, ensure_ascii=False)
                            + "\nChoose the best next task and the best available agent for it."
                        ),
                    }
                )
                emitter.emit("orchestrator.started", {"step": step, "mode": "dispatch"})
                try:
                    decision = orchestrator_agent.decide_next_action(orchestration_messages)
                except Exception as exc:
                    decision = _fallback_orchestrator_decision(
                        ready_tasks=ready_tasks,
                        agents=agents,
                        error=exc,
                    )
                    session.add_message(
                        {
                            "role": "assistant",
                            "content": (
                                "Orchestrator returned an invalid dispatch decision, so the runtime selected "
                                f"{decision.task_key} for {decision.agent_name}. "
                                f"Reason: {safe_exception_summary(exc, max_chars=300)}"
                            ),
                        }
                    )
                emitter.emit(
                    "orchestrator.decision",
                    {"action": decision.action, "description": decision.description, "task_key": decision.task_key},
                )
                session.add_message({"role": "assistant", "content": decision.description})

                if decision.action == "ask_user":
                    emitter.emit("input.required", {"question": decision.description})
                    user_response = wait_for_input(decision.description)
                    if is_cancelled():
                        raise RunCancelled()
                    session.add_message({"role": "user", "content": user_response})
                    objective = board.objective(user_response)
                    continue

                if decision.action == "finish":
                    finalized, final_response = _finalize_completed_work(
                        board=board,
                        response_agent=response_agent,
                        session=session,
                        response_context_budget=response_context_budget,
                        response_schema_source=response_schema_source,
                        emitter=emitter,
                        is_cancelled=is_cancelled,
                        completion_note=(
                            "Summarize the completed work in the required JSON structure. "
                            "Use the validated task board report as evidence. "
                            "Never invent filenames or claim work was tested without evidence."
                        ),
                    )
                    if finalized:
                        return final_response
                    session.add_message(
                        {
                            "role": "user",
                            "content": "Finish rejected because the task board still has open work. Continue orchestration.",
                        }
                    )
                    objective = board.objective("")
                    continue

                delegated_agent = _find_agent_by_name(agents, decision.agent_name)
                if delegated_agent is None:
                    session.add_message(
                        {
                            "role": "user",
                            "content": f"Delegation rejected because agent {decision.agent_name} is unavailable.",
                        }
                    )
                    continue

                task = board.get_task(task_key=decision.task_key) or board.next_ready()
                if task is None or task["status"] != "ready":
                    session.add_message(
                        {
                            "role": "user",
                            "content": "Delegation rejected because the chosen task is not ready anymore. Pick another ready task.",
                        }
                    )
                    continue

                if _requires_bootstrap_before_dispatch(board, task):
                    session.add_message(
                        {
                            "role": "user",
                            "content": (
                                "Delegation rejected because this broad collection-wide task must not run yet. "
                                "Dispatch the outstanding inspect, inventory, or per-file task-seeding work first "
                                "so the runtime can create durable file-level tasks."
                            ),
                        }
                    )
                    continue

                delegation_instructions = _build_delegation_instructions(task, decision.description)
                task = board.begin_task(task["id"], delegated_agent.name, delegation_instructions)
                emitter.emit(
                    "agent.delegated",
                    {"agent": delegated_agent.name, "task_id": task["id"], "task_key": task["task_key"]},
                )
                session.add_message(
                    {
                        "role": "assistant",
                        "content": f"Delegated {task['task_key']} to {delegated_agent.name}: {delegation_instructions}",
                    }
                )

                agent_messages = session.get_bounded_context(
                    max_recent_messages=12,
                    max_context_chars=delegated_context_budget,
                )
                worker_query = " ".join(
                    part for part in [task.get("title", ""), task.get("description", ""), delegation_instructions] if part
                )
                worker_retrieval = self._build_retrieval_context(session, worker_query, delegated_context_budget)
                if worker_retrieval:
                    agent_messages.insert(0, {"role": "system", "content": worker_retrieval})
                agent_messages.append(
                    {
                        "role": "user",
                        "content": (
                            EXECUTION_POLICY
                            + "\nCurrent objective: "
                            + objective
                            + "\nCurrent delegated task: "
                            + json.dumps(task, ensure_ascii=False)
                            + "\nTask board summary: "
                            + json.dumps(board.summary(), ensure_ascii=False)
                            + "\nComplete only this task. Use task_board(action='current' or 'get') to inspect it. "
                            + "For large directories prefer workspace_fs(action='snapshot') before many smaller reads. "
                            + "Use task_board(action='remember') for durable intermediate findings another agent may need. "
                            + "When the work is done, report back with task_board(action='submit') including a concise summary, concrete evidence, and exact artifact paths. "
                            + "If you are blocked, use task_board(action='block') with the real reason."
                        ),
                    }
                )

                try:
                    delegated_agent.chat(
                        agent_messages,
                        session,
                        emit=lambda event_type, data: emitter.emit(event_type, data),
                        is_cancelled=is_cancelled,
                        max_iterations=int(config.get("max_worker_iterations", 100)),
                    )
                except BudgetExhausted:
                    emitter.emit("agent.yielded", {"agent": delegated_agent.name, "reason": "iteration_budget"})
                    session.add_message(
                        {
                            "role": "assistant",
                            "content": (
                                f"Worker batch for {task['task_key']} ended before a final report. "
                                "Resume from task_board state and archived tool results."
                            ),
                        }
                    )

                task_after = board.get_task(task_id=task["id"])
                task_after = _auto_submit_seed_task(board, task_after, delegated_agent.name)
                task_after = _auto_submit_completed_artifact_task(board, task_after, delegated_agent.name)
                if task_after is not None and task_after["status"] == "in_progress":
                    board.block(
                        task["id"],
                        "Worker returned control without submitting a task report.",
                        delegated_agent.name,
                    )
                    task_after = board.get_task(task_id=task["id"])

                if task_after is not None and task_after["status"] in {"reported", "blocked"}:
                    session.add_message(
                        {
                            "role": "assistant",
                            "content": (
                                f"Task {task_after['task_key']} status={task_after['status']}. "
                                f"Summary: {task_after.get('result_summary') or 'n/a'}. "
                                f"Evidence: {task_after.get('evidence') or task_after.get('last_error') or 'n/a'}"
                            ),
                        }
                    )

                emitter.emit(
                    "agent.batch.completed",
                    {
                        "agent": delegated_agent.name,
                        "task_id": task["id"],
                        "task_status": task_after["status"] if task_after else "unknown",
                        "remaining": board.summary()["remaining"],
                    },
                )
            finally:
                step += 1

        emitter.emit("run.force_finished", {"reason": "step_budget_reached", "max_steps": config["max_steps"]})
        if response_agent is not None:
            coverage = board.verify()
            emitter.emit("work.coverage", coverage)
            final_messages = session.get_bounded_context(
                max_recent_messages=20,
                max_context_chars=response_context_budget,
            )
            final_messages.append(
                {
                    "role": "user",
                    "content": (
                        "The orchestration step budget was reached before the task board fully completed. "
                        "Summarize the actual state honestly in the required JSON structure, including what "
                        "was validated, what remains open, and any blockers.\n"
                        + json.dumps(
                            {
                                "completion_report": board.completion_report(),
                                "coverage": coverage,
                                "recent_activity": board.recent_activity(limit=12),
                            },
                            ensure_ascii=False,
                        )
                    ),
                }
            )
            final_response = response_agent.chat_structured(
                messages=final_messages,
                schema_source=response_schema_source,
                session=session,
            )
            if is_cancelled():
                raise RunCancelled()
            raise IncompleteRun(
                "Run step budget reached before the task board fully completed; resume this session to continue durable work.",
                final_response=final_response,
            )

        raise BudgetExhausted("Run step budget reached; resume this session to continue durable work.")
