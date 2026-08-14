"""Semantic run events for the agent loop.

Instead of streaming raw chain-of-thought, the runner emits structured,
sequenced events describing what is happening (delegations, tool calls,
decisions) so a GUI/service can render live activity without exposing
private reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict

RUN_STARTED = "run.started"
STEP_STARTED = "step.started"
ORCHESTRATOR_STARTED = "orchestrator.started"
ORCHESTRATOR_DECISION = "orchestrator.decision"
AGENT_DELEGATED = "agent.delegated"
AGENT_MESSAGE_DELTA = "agent.message.delta"
AGENT_MESSAGE_COMPLETED = "agent.message.completed"
TOOL_STARTED = "tool.started"
TOOL_COMPLETED = "tool.completed"
INPUT_REQUIRED = "input.required"
RESPONSE_STARTED = "response.started"
RUN_COMPLETED = "run.completed"
RUN_FAILED = "run.failed"
RUN_CANCELLED = "run.cancelled"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunEvent:
    run_id: str
    session_id: str
    sequence: int
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)


EventSink = Callable[[RunEvent], None]


class ConsoleEventSink:
    """Prints events to stdout - used by the CLI adapter."""

    def __call__(self, event: RunEvent) -> None:
        print(f"[{event.type}] {event.data}")


class EventEmitter:
    """Assigns monotonically increasing sequence numbers and forwards to a sink."""

    def __init__(self, run_id: str, session_id: str, sink: EventSink):
        self.run_id = run_id
        self.session_id = session_id
        self.sink = sink
        self._sequence = 0

    def emit(self, event_type: str, data: Dict[str, Any] | None = None) -> RunEvent:
        self._sequence += 1
        event = RunEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            sequence=self._sequence,
            type=event_type,
            data=data or {},
        )
        self.sink(event)
        return event
