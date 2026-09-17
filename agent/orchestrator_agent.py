from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal, Optional, Type, TypeVar, Union

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator
from typing_extensions import Self

from agent.context_guard import ContextLimits, ContextWindowGuard
from agent.generic_agent import GenericAgent
from agent.llm import create_client, generation_options, normalize_chat_messages

ResponseT = TypeVar("ResponseT", bound=BaseModel)


TASK_TYPES = Literal[
    "analysis",
    "research",
    "implementation",
    "verification",
    "documentation",
    "coordination",
    "other",
]


class PlannedTaskBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_key: str = Field(description="Stable task key such as TASK-ANALYZE-API.")
    title: str = Field(description="Short human-readable task title.")
    description: str = Field(description="Precise task description.")
    task_type: TASK_TYPES = Field(description="Type of work required.")
    priority: int = Field(ge=1, le=100, description="Lower number means earlier execution.")
    depends_on_keys: list[str] = Field(default_factory=list, description="Task keys that must finish first.")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Observable completion checks.")


class OrchestratorDecisionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["ask_user", "delegate_to_agent", "finish"] = Field(
        description="Next runtime action."
    )
    description: str = Field(description="Delegation instructions or the question/result summary.")
    task_key: Optional[str] = Field(default=None, description="Task key when delegating, else null.")

    @model_validator(mode="before")
    @classmethod
    def normalize_non_delegation_task(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if value.get("action") != "delegate_to_agent":
            normalized = dict(value)
            normalized["task_key"] = None
            normalized["agent_name"] = None
            return normalized
        return value

    @model_validator(mode="after")
    def validate_delegation_fields(self) -> Self:
        agent_name = getattr(self, "agent_name", None)
        if self.action == "delegate_to_agent":
            if not self.task_key:
                raise ValueError("task_key is required when delegating")
            if not agent_name:
                raise ValueError("agent_name is required when delegating")
        else:
            if self.task_key is not None:
                raise ValueError("task_key must be null unless delegating")
            if agent_name is not None:
                raise ValueError("agent_name must be null unless delegating")
        return self


class TaskReviewBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["accept", "rework", "cancel", "ask_user"] = Field(
        description="How the orchestrator wants to resolve the worker report."
    )
    validation_notes: str = Field(description="Validation result or the follow-up question.")


def _planned_task_model(available_agents: Iterable[str]) -> type[BaseModel]:
    agent_names = tuple(dict.fromkeys(available_agents))
    if not agent_names:
        raise ValueError("No agent available")
    AgentName = Literal.__getitem__(agent_names)
    return create_model(
        "PlannedTask",
        __base__=PlannedTaskBase,
        suggested_agent=(
            Optional[AgentName],
            Field(default=None, description="Best available agent for this task, if clear."),
        ),
    )


def create_task_planning_response(available_agents: Iterable[str]) -> type[BaseModel]:
    planned_task_model = _planned_task_model(available_agents)
    return create_model(
        "TaskPlanningResponse",
        summary=(str, Field(description="Short planning summary.")),
        tasks=(list[planned_task_model], Field(description="Ordered task list.")),
        __base__=BaseModel,
    )


def create_orchestrator_decision(available_agents: Iterable[str]) -> type[BaseModel]:
    agent_names = tuple(dict.fromkeys(available_agents))
    if not agent_names:
        raise ValueError("No agent available")
    AgentName = Literal.__getitem__(agent_names)
    return create_model(
        "OrchestratorDecision",
        __base__=OrchestratorDecisionBase,
        agent_name=(
            Optional[AgentName],
            Field(
                default=None,
                description="Must be one of the available agent names when delegating, else null.",
            ),
        ),
    )


def create_task_review_response(available_agents: Iterable[str]) -> type[BaseModel]:
    planned_task_model = _planned_task_model(available_agents)
    return create_model(
        "TaskReviewResponse",
        __base__=TaskReviewBase,
        new_tasks=(
            list[planned_task_model],
            Field(default_factory=list, description="Optional follow-up tasks discovered during review."),
        ),
    )


def create_orchestrator_response(available_agents: Iterable[str]) -> type[BaseModel]:
    return create_orchestrator_decision(available_agents)


class OrchestratorAgent:
    id: int
    name: str
    system_message: str
    agentmd: str
    skillsmd: str
    resources_path: str
    workspace_path: str
    model: str
    api_key: str
    base_url: str
    temperature: float
    context_limits: ContextLimits
    context_guard: ContextWindowGuard
    client: Union[OpenAI, Any]
    available_agents: list[str]
    planning_model: Type[BaseModel]
    decision_model: Type[BaseModel]
    review_model: Type[BaseModel]

    def __init__(
        self,
        id,
        name,
        model,
        api_key,
        base_url,
        temperature,
        resources_path,
        workspace_path,
        available_agents,
        context_limits: dict[str, Any] | None = None,
        llm_options: dict[str, Any] | None = None,
    ):
        self.llm_options = dict(llm_options or {})
        self.id = id
        self.name = name
        self.resources_path = resources_path
        self.workspace_path = workspace_path
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.context_limits = ContextLimits.from_dict(context_limits)
        self.context_guard = ContextWindowGuard(self.context_limits)
        self.agentmd = self.load_agentmd(self.name)
        self.skillsmd = self.load_skillsmd(self.name)
        self.client = self.init_client()
        self.available_agents = list(dict.fromkeys(available_agents))
        self.planning_model = create_task_planning_response(self.available_agents)
        self.decision_model = create_orchestrator_decision(self.available_agents)
        self.review_model = create_task_review_response(self.available_agents)
        self.system_message = self.context_guard.trim_system_message(self.create_system_message())

    def load_agentmd(self, agent_name: str) -> str:
        path = self.resources_path + "/" + agent_name + "/AGENT.md"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def load_skillsmd(self, agent_name: str) -> str:
        path = self.resources_path + "/" + agent_name + "/SKILLS.md"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def init_client(self):
        return create_client(self.api_key, self.base_url, self.llm_options)

    def create_system_message(self) -> str:
        sys_msg = self.agentmd + self.skillsmd
        sys_msg += "\n\nIMPORTANT ORCHESTRATION RULES\n"
        sys_msg += "- The SQLite task board is the runtime source of truth for planning, task order, assignment, and completion.\n"
        sys_msg += "- Break work into small tasks with explicit acceptance criteria and sensible dependencies.\n"
        sys_msg += "- Delegate to the best available agent for the specific task, not for the whole project at once.\n"
        sys_msg += "- A worker report is not accepted automatically; review it, validate it against evidence, then either accept it, return it for rework, cancel it, or ask the user.\n"
        sys_msg += "- Finish only when all task-board tasks are validated or cancelled and the user goal is satisfied.\n"
        sys_msg += "\nAVAILABLE AGENTS\n"
        for agent_name in self.available_agents:
            sys_msg += f"OFFICIAL AGENT NAME: {agent_name}\n"
            sys_msg += self.load_agentmd(agent_name)
            sys_msg += self.load_skillsmd(agent_name)
        return sys_msg

    def _chat_parse(self, messages: list[dict], response_model: type[ResponseT]) -> ResponseT:
        completion = None
        last_error: Exception | None = None
        for attempt in range(1, self.context_limits.max_retries + 1):
            bounded_messages = self.context_guard.trim_messages(messages, attempt=attempt)
            bounded_messages = normalize_chat_messages(bounded_messages, self.system_message)
            try:
                completion = self.client.beta.chat.completions.parse(
                    model=self.model,
                    messages=bounded_messages,
                    response_format=response_model,
                    **generation_options(self.llm_options, self.temperature),
                )
                break
            except Exception as exc:
                last_error = exc
                if not self.context_guard.is_context_length_error(exc):
                    raise

        if completion is None:
            raise RuntimeError("Failed to parse orchestrator response after context trimming retries.") from last_error

        return completion.choices[0].message.parsed

    def plan_tasks(self, messages: list[dict]) -> BaseModel:
        return self._chat_parse(messages, self.planning_model)

    def decide_next_action(self, messages: list[dict]) -> BaseModel:
        return self._chat_parse(messages, self.decision_model)

    def review_task(self, messages: list[dict]) -> BaseModel:
        return self._chat_parse(messages, self.review_model)
