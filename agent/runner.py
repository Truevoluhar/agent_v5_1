"""Reusable, in-process agent execution loop.

Extracted from the old agent/cli.py main() so it can be driven by multiple
front ends: the CLI (blocking input()/print()), and the long-running
service/api.py (persisted events, queued input, cancellable).
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from dotenv import load_dotenv


import yaml

from agent.execution import RunCancelled, BudgetExhausted, EXECUTION_POLICY, workspace_lock
from agent.llm import safe_endpoint, safe_exception_summary
from agent.work_queue import WorkQueue
from agent.events import EventEmitter, EventSink
from agent.generic_agent import GenericAgent
from agent.orchestrator_agent import OrchestratorAgent
from agent.paths import DATA_ROOT
from agent.response_agent import ResponseAgent
from agent.session import Session
from agent.user_storage import user_storage_paths

AGENT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = str(AGENT_ROOT / "config.yml")
DEFAULT_PLAN_FILENAME = "PLAN.md"
PLAN_OWNER_FILENAME = ".agent/active-plan.json"
MAX_PLAN_CONTEXT_CHARS = 12_000

WaitForInput = Callable[[str], str]
IsCancelled = Callable[[], bool]
logger = logging.getLogger(__name__)


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


def _prepare_plan_for_new_session(workspace_path: str, session_id: str) -> dict:
    """Give a new session a fresh active plan without discarding the previous one."""
    workspace = Path(workspace_path)
    plan_path = workspace / DEFAULT_PLAN_FILENAME
    owner_path = workspace / PLAN_OWNER_FILENAME
    archived_to = None
    if plan_path.exists():
        archive_dir = workspace / "plan" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived_to = archive_dir / f"PLAN_{timestamp}_{session_id[:8]}_previous-session.md"
        plan_path.replace(archived_to)
    owner_path.parent.mkdir(parents=True, exist_ok=True)
    owner_path.write_text(json.dumps({"session_id": session_id, "state": "awaiting_plan"}), encoding="utf-8")
    return {"archived_to": str(archived_to) if archived_to else None, "owner": str(owner_path)}


def _read_active_plan_context(workspace_path: str, session_id: str | None = None,
                              filename: str = DEFAULT_PLAN_FILENAME) -> tuple[str | None, dict]:
    plan_path = Path(workspace_path) / filename
    if not plan_path.exists():
        return None, {"exists": False, "path": str(plan_path)}

    owner_path = Path(workspace_path) / PLAN_OWNER_FILENAME
    if session_id and owner_path.exists():
        try:
            owner = json.loads(owner_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            owner = {}
        if owner.get("session_id") != session_id:
            return None, {"exists": True, "path": str(plan_path), "owned_by_other_session": True}

    content = plan_path.read_text(encoding="utf-8")
    metadata = {"exists": True, "path": str(plan_path), "chars": len(content), "truncated": False}

    if len(content) > MAX_PLAN_CONTEXT_CHARS:
        metadata["truncated"] = True
        content = content[:MAX_PLAN_CONTEXT_CHARS] + "\n\n[TRUNCATED PLAN CONTEXT]"

    return content, metadata


def _find_agent_by_name(agents: list[GenericAgent], agent_name: str) -> GenericAgent | None:
    for agent in agents:
        if agent.name == agent_name:
            return agent
    return None


def _planner_name(agents: list[GenericAgent]) -> str | None:
    planner_agent = _find_agent_by_name(agents, "PLANNER")
    return planner_agent.name if planner_agent is not None else None


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

        # Workspace: honor the caller-provided workspace instead of always
        # falling back to the global config value (previously --workspace was
        # parsed but silently ignored).
        workspace_value = request.workspace or config["workspace"]
        agent_workspace = str(DATA_ROOT / workspace_value) if workspace_value else str(DATA_ROOT)
        Path(f"{agent_workspace}/plan").mkdir(parents=True, exist_ok=True)

        session = Session(
            id=request.session_id,
            session_folder=user_storage.session_folder,
            workspace_folder=agent_workspace,
            memory_folder=user_storage.memory_folder,
        )
        if session.is_new:
            session.set_name(self._generate_session_name(request.prompt))
            plan_reset = _prepare_plan_for_new_session(agent_workspace, session.id)
            if plan_reset["archived_to"]:
                logger.info("Archived prior active plan for new session session_id=%s archive=%s",
                            session.id, plan_reset["archived_to"])

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

        available_agents = [agent.name for agent in agents]

        orchestrator_agent = OrchestratorAgent(
            id="orchestrator_agent",
            name=orchestrator_config["name"],
            model=orchestrator_config["model"],
            temperature=orchestrator_config["temperature"],
            base_url=orchestrator_config["base_url"],
            api_key=os.getenv(orchestrator_config["api_key"]),
            resources_path=agent_resources,
            workspace_path=agent_workspace,
            available_agents=available_agents,
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
        return RunResult(
            run_id=run_id, session_id=session.id, status="completed", final_response=final_response
        )


    @staticmethod
    def _generate_session_name(prompt: str) -> str:
        """Create a useful title without making an extra provider request.

        Session naming is metadata and must not delay, consume tokens from, or
        produce misleading connection warnings before the actual run starts.
        """
        plain_text = re.sub(r"[`#*_>\[\]{}()]", " ", str(prompt or ""))
        words = plain_text.split()
        if not words:
            return "New chat"
        return " ".join(words[:8])[:120]

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
        queue = WorkQueue(agent_workspace, session.id)
        objective = next((m.get("content", "") for m in reversed(session.messages) if m.get("role") == "user"), "")
        objective = queue.objective(str(objective))
        for step in range(config["max_steps"]):
            if is_cancelled():
                raise RunCancelled()

            emitter.emit("step.started", {"step": step})

            recent_query = next(
                (
                    message.get("content")
                    for message in reversed(session.messages)
                    if message.get("role") == "user" and message.get("content")
                ),
                None,
            )
            historical_context = ""
            if recent_query:
                retrieval_limit = Session.suggest_retrieval_limit(
                    context_budget_chars=orchestrator_context_budget // 5,
                    min_limit=1,
                    max_limit=6,
                    chars_per_match=450,
                )
                historical_context = session.format_retrieval_context(
                    query=recent_query,
                    limit=retrieval_limit,
                    max_chars=max(600, orchestrator_context_budget // 6),
                )

            plan_text, _ = _read_active_plan_context(agent_workspace, session.id)

            orchestrator_messages = session.get_bounded_context(
                max_recent_messages=12,
                max_context_chars=orchestrator_context_budget,
            )
            if plan_text is not None:
                orchestrator_messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": (
                            "Active plan (source of truth). Follow this plan and update it "
                            f"instead of creating a separate one.\n\n{plan_text}"
                        ),
                    },
                )
            else:
                orchestrator_messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": (
                            "No active plan file found at PLAN.md. "
                            "Delegate to PLANNER to create one before substantial implementation tasks."
                        ),
                    },
                )

            if historical_context:
                orchestrator_messages.insert(0, {"role": "system", "content": historical_context})

            durable_context = (EXECUTION_POLICY + "\nCurrent objective: " + str(objective)
                               + "\nDurable work status: " + json.dumps(queue.summary()))
            orchestrator_messages.append({"role": "user", "content": durable_context})
            emitter.emit("orchestrator.started", {"step": step})
            orchestrator_response = orchestrator_agent.chat_structured(messages=orchestrator_messages)
            emitter.emit(
                "orchestrator.decision",
                {"action": orchestrator_response.action, "description": orchestrator_response.description},
            )

            session.add_message({"role": "assistant", "content": orchestrator_response.description})

            if orchestrator_response.action == "delegate_to_agent":
                delegated_name = orchestrator_response.agent_name
                planner = _planner_name(agents)

                if plan_text is None and planner is not None and delegated_name != planner:
                    delegated_name = planner
                    session.add_message(
                        {
                            "role": "system",
                            "content": (
                                "Delegation overridden to PLANNER because no active PLAN.md exists yet. "
                                "Create/refresh PLAN.md first."
                            ),
                        }
                    )

                delegated_agent = _find_agent_by_name(agents, delegated_name)
                if delegated_agent is not None:
                    emitter.emit("agent.delegated", {"agent": delegated_agent.name})

                    # Every delegation has a durable unit of work. This prevents a
                    # worker from treating exploratory shell output as completion.
                    queue_before = queue.summary()
                    if not queue_before["remaining"]:
                        created = queue.add(
                            f"{delegated_agent.name}: {orchestrator_response.description}"
                        )
                        queue_before = queue.summary()
                        logger.info("Created delegated work item run_session=%s task_id=%s agent=%s",
                                    session.id, created["id"], delegated_agent.name)

                    worker_context = (EXECUTION_POLICY + "\nCurrent objective: " + str(objective)
                                      + "\nDurable work status: " + json.dumps(queue_before))

                    agent_messages = session.get_bounded_context(
                        max_recent_messages=12,
                        max_context_chars=delegated_context_budget,
                    )

                    if plan_text is not None:
                        agent_messages.insert(
                            0,
                            {
                                "role": "system",
                                "content": (
                                    "Execution must follow active PLAN.md. "
                                    "If work changes scope, update PLAN.md first, then continue.\n" + plan_text
                                ),
                            },
                        )

                    agent_messages.append({"role": "user", "content": (
                        worker_context + "\nDelegated task: " + orchestrator_response.description
                        + "\nYou must call work_queue(action='next') before run_shell. "
                        "Complete the claimed item with evidence and artifact paths, or mark it failed with a reason. "
                        "Do not report this delegation as complete until the queue records it."
                    )})
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
                        session.add_message({"role": "assistant", "content":
                            "Worker batch ended. Resume from work_queue and archived tool results; work is not yet complete."})
                    queue_after = queue.summary()
                    emitter.emit("agent.batch.completed", {
                        "agent": delegated_agent.name,
                        "remaining": queue_after["remaining"],
                        "counts": queue_after["counts"],
                    })
                    if queue_after["remaining"]:
                        session.add_message({"role": "system", "content": (
                            "The delegated worker returned, but durable work remains. "
                            "Do not treat its narrative as completion; delegate the queue's next item or resolve its failure."
                        )})


            if orchestrator_response.action == "ask_user":
                emitter.emit("input.required", {"question": orchestrator_response.description})
                user_response = wait_for_input(orchestrator_response.description)
                if is_cancelled():
                    raise RunCancelled()
                session.add_message({"role": "user", "content": user_response})
                objective += "\nUser clarification: " + user_response

            if is_cancelled():
                raise RunCancelled()
            should_finalize = orchestrator_response.action == "finish"
            if should_finalize:
                coverage = queue.verify()
                emitter.emit("work.coverage", coverage)
                if coverage["remaining"]:
                    session.add_message({"role": "user", "content":
                        "Completion rejected: durable queue has unfinished or invalidated tasks. Resume work_queue next; resolve failures before finishing."})
                    continue

            if should_finalize:
                if response_agent is not None:
                    emitter.emit("response.started", {})
                    final_messages = session.get_bounded_context(
                        max_recent_messages=20,
                        max_context_chars=response_context_budget,
                    )
                    final_messages.append(
                        {
                            "role": "user",
                            "content": ("Summarize the completed work in the required JSON structure. "
                                        "Use the following verified artifact paths and counts as evidence. "
                                        "Never invent filenames or claim content was tested without evidence.\n"
                                        + json.dumps(queue.completion_report())),
                        }
                    )
                    final_response = response_agent.chat_structured(
                        messages=final_messages,
                        schema_source=response_schema_source,
                        session=session,
                    )
                    if is_cancelled():
                        raise RunCancelled()
                    return final_response
                return None

        raise BudgetExhausted("Run step budget reached; resume this session to continue durable work.")
