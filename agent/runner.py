"""Reusable, in-process agent execution loop.

Extracted from the old agent/cli.py main() so it can be driven by multiple
front ends: the CLI (blocking input()/print()), and the long-running
service/api.py (persisted events, queued input, cancellable).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import yaml
from openai import OpenAI

from agent.context_guard import ContextLimits, ContextWindowGuard
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
MAX_PLAN_CONTEXT_CHARS = 12_000

WaitForInput = Callable[[str], str]
IsCancelled = Callable[[], bool]


class RunCancelled(Exception):
    """Raised internally when a caller requests cancellation mid-run."""


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


def _read_active_plan_context(workspace_path: str, filename: str = DEFAULT_PLAN_FILENAME) -> tuple[str | None, dict]:
    plan_path = Path(workspace_path) / filename
    if not plan_path.exists():
        return None, {"exists": False, "path": str(plan_path)}

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

    def __init__(self, config_path: str = CONFIG_PATH):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def run(
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
            session.set_name(
                self._generate_session_name(
                    prompt=request.prompt,
                    agent_config=orchestrator_config,
                    context_limits=context_limits,
                )
            )

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
        except RunCancelled:
            emitter.emit("run.cancelled", {})
            return RunResult(run_id=run_id, session_id=session.id, status="cancelled")
        except Exception as exc:
            emitter.emit("run.failed", {"error": str(exc)})
            return RunResult(run_id=run_id, session_id=session.id, status="failed", error=str(exc))

        emitter.emit("run.completed", {})
        return RunResult(
            run_id=run_id, session_id=session.id, status="completed", final_response=final_response
        )

    @staticmethod
    def _generate_session_name(
        *,
        prompt: str,
        agent_config: dict[str, Any],
        context_limits: dict[str, Any],
    ) -> str:
        fallback_name = "New chat"
        guard = ContextWindowGuard(ContextLimits.from_dict(context_limits))
        input_items = guard.trim_response_input_items(
            [{"role": "user", "content": prompt}],
            attempt=1,
        )
        if not input_items:
            return fallback_name

        client_kwargs = {"api_key": os.getenv(agent_config["api_key"])}
        if agent_config.get("base_url"):
            client_kwargs["base_url"] = agent_config["base_url"]

        client = OpenAI(**client_kwargs)
        instructions = (
            "Create a concise, descriptive title for this new conversation. "
            "Return only the title, with no quotation marks, markdown, or punctuation at the end. "
            "Use at most 8 words."
        )
        last_error: Exception | None = None
        for attempt in range(1, guard.limits.max_retries + 1):
            try:
                response = client.responses.create(
                    model=agent_config["model"],
                    instructions=instructions,
                    input=guard.trim_response_input_items(input_items, attempt=attempt),
                    temperature=agent_config.get("temperature", 1.0),
                )
                title = " ".join((response.output_text or "").split())[:120]
                return title or fallback_name
            except Exception as exc:
                last_error = exc
                if not guard.is_context_length_error(exc):
                    break

        if last_error is not None:
            print(f"[Session] Could not generate session name: {last_error}")
        return fallback_name

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

            plan_text, _ = _read_active_plan_context(agent_workspace)

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
                                    "If work changes scope, update PLAN.md first, then continue."
                                ),
                            },
                        )

                    delegated_agent.chat(
                        agent_messages,
                        session,
                        emit=lambda event_type, data: emitter.emit(event_type, data),
                    )

            if orchestrator_response.action == "ask_user":
                emitter.emit("input.required", {"question": orchestrator_response.description})
                user_response = wait_for_input(orchestrator_response.description)
                session.add_message({"role": "user", "content": user_response})

            should_finalize = orchestrator_response.action == "finish" or (
                step == config["max_steps"] - 1 and orchestrator_response.action != "ask_user"
            )

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
                            "content": "Summarize the completed work in the required JSON structure.",
                        }
                    )
                    final_response = response_agent.chat_structured(
                        messages=final_messages,
                        schema_source=response_schema_source,
                        session=session,
                    )
                    return final_response
                return None

        return None
