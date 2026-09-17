import json
import uuid
from pathlib import Path

from agent.execution import BudgetExhausted, RunCancelled, EXECUTION_POLICY
from agent.work_queue import TaskBoard
from typing import Any, Callable, Union

from openai import OpenAI

from agent.llm import create_client, generation_options, create_tool_response
from agent.context_guard import ContextLimits, ContextWindowGuard
from agent.tools.tools_registry import get_tool_schemas, execute_registered_tool
from agent.session import Session

        

class GenericAgent:

    id: int

    name: str
    
    agentmd: str
    skillsmd: str
    system_message: str
    
    resources_path: str
    workspace_path: str

    model: str
    api_key: str
    base_url: str
    temperature: float
    context_limits: ContextLimits
    context_guard: ContextWindowGuard
    
    client: Union[OpenAI, Any]



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

        self.agentmd = self.load_agentmd()
        self.skillsmd = self.load_skillsmd()
        self.system_message = self.context_guard.trim_system_message(
            self.create_system_message()
        )
        
        self.client = self.init_client()



    def load_agentmd(self) -> None:

        print(f"[Agent] Loading AGENT.md ...")

        path = self.resources_path + "/" + self.name + "/AGENT.md"
        with open(path, "r") as f:
            content = f.read()
            return content
        
    
    def load_skillsmd(self) -> None:

        print(f"[Agent] Loading SKILLS.md ...")

        path = self.resources_path + "/" + self.name + "/SKILLS.md"
        with open(path, "r") as f:
            content = f.read()
            return content
        
    
    def create_system_message(self):

        sys_msg = ""

        sys_msg += self.agentmd
        sys_msg += self.skillsmd
        
        return sys_msg
    
    
    
    def init_client(self) -> None:

        return create_client(self.api_key, self.base_url, self.llm_options)



    def _to_responses_tools(self, chat_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:

        response_tools: list[dict[str, Any]] = []

        for tool in chat_tools:
            if tool.get("type") != "function":
                response_tools.append(tool)
                continue

            # Support both Chat Completions and already-flattened schemas.
            function = tool.get("function", tool)

            converted: dict[str, Any] = {
                "type": "function",
                "name": function["name"],
                "description": function.get("description", ""),
                "parameters": function.get(
                    "parameters",
                    {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
            }

            if "strict" in function:
                converted["strict"] = function["strict"]

            response_tools.append(converted)

        return response_tools


    def chat(self, messages: list[dict], session: Session, emit: Callable[[str, dict], None] | None = None,
             is_cancelled: Callable[[], bool] | None = None, max_iterations: int = 100) -> str:
        is_cancelled = is_cancelled or (lambda: False)
        def check_cancelled():
            if is_cancelled():
                raise RunCancelled()
        check_cancelled()
        scope = getattr(session, "id", "default")
        pinned = "\n\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
        instructions = (EXECUTION_POLICY + "\n"
                        + self.system_message[:self.context_limits.max_system_message_chars // 2]
                        + "\n" + pinned)
        instructions = self.context_guard.trim_system_message(instructions)
        chat_tools = get_tool_schemas()
        tools = self._to_responses_tools(chat_tools)

        # Responses accepts user/assistant conversational messages.
        # Old Chat Completions tool messages cannot be copied directly.
        input_items = [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in messages
            if message.get("role") in {"user", "assistant"}
            and message.get("content") is not None
        ]

        if not input_items:
            raise ValueError("No user or assistant messages were supplied.")

        response = None
        last_error: Exception | None = None
        for attempt in range(1, self.context_limits.max_retries + 1):
            bounded_input_items = self.context_guard.trim_response_input_items(
                input_items,
                attempt=attempt,
            )

            if not bounded_input_items:
                raise ValueError("No user or assistant messages remained after bounding input.")

            try:
                response = create_tool_response(self.client,
                    model=self.model,
                    instructions=instructions,
                    input=bounded_input_items,
                    tools=tools,
                    options=self.llm_options,
                    temperature=self.temperature,
                )
                break
            except Exception as exc:
                last_error = exc
                if not self.context_guard.is_context_length_error(exc):
                    raise

        if response is None:
            raise RuntimeError(
                "Failed to create initial model response after context trimming retries."
            ) from last_error

        response_input_items: list[Any] = list(bounded_input_items)

        for iteration in range(max_iterations + 1):
            check_cancelled()
            tool_calls = [
                item
                for item in response.output
                if item.type == "function_call"
            ]

            if not tool_calls:
                final_text = response.output_text

                if not final_text:
                    raise RuntimeError(
                        "The model returned neither function calls nor text. "
                        f"Status: {response.status}"
                    )

                assistant_message = {
                    "role": "assistant",
                    "content": final_text,
                }
                session.add_message(assistant_message)

                if emit is not None:
                    emit("agent.message.completed", {"agent": self.name, "content": final_text})

                return final_text

            if iteration == max_iterations:
                raise BudgetExhausted("Worker batch budget reached; continue from durable state.")

            tool_outputs: list[dict[str, Any]] = []

            for tool_call in tool_calls:
                check_cancelled()
                tool_name = tool_call.name

                try:
                    arguments = json.loads(tool_call.arguments)
                except json.JSONDecodeError as exc:
                    tool_result: Any = {
                        "error": (
                            f"Invalid JSON arguments for tool "
                            f"{tool_name}: {exc}"
                        )
                    }
                else:
                    print(f"[{self.name}]: Tool call: {tool_name}")
                    if emit is not None:
                        emit("tool.started", {"agent": self.name, "tool": tool_name})

                    try:
                        tool_result = execute_registered_tool(
                            workspace=self.workspace_path,
                            tool_name=tool_name,
                            tool_input=arguments,
                            scope=scope,
                            is_cancelled=is_cancelled,
                        )
                        if emit is not None:
                            metadata = tool_result.get("metadata") or {}
                            emit("tool.completed", {
                                "agent": self.name,
                                "tool": tool_name,
                                "ok": bool(tool_result.get("ok", False)),
                                "cwd": metadata.get("cwd"),
                                "exit_code": metadata.get("exit_code"),
                                "log_file": metadata.get("log_file"),
                                "error": tool_result.get("error"),
                            })
                    except RunCancelled:
                        raise
                    except Exception as exc:
                        # Return the error to the model so it can recover,
                        # select another tool, or explain the failure.
                        tool_result = {
                            "error": f"{type(exc).__name__}: {exc}"
                        }
                        if emit is not None:
                            emit("tool.completed", {"agent": self.name, "tool": tool_name, "ok": False})

                log_dir = Path(self.workspace_path) / ".agent" / "tool-results"
                log_dir.mkdir(parents=True, exist_ok=True)
                log_path = log_dir / (uuid.uuid4().hex + ".json")
                raw_result = json.dumps(tool_result, ensure_ascii=False, default=str)
                log_path.write_text(json.dumps({"tool": tool_name, "arguments": tool_call.arguments,
                                                "result": tool_result}, ensure_ascii=False, default=str), encoding="utf-8")
                serialized_result = self.context_guard.trim_tool_output(tool_result)
                if len(raw_result) > self.context_limits.max_tool_output_chars:
                    serialized_result = json.dumps({
                        "ok": tool_result.get("ok", False),
                        "preview": serialized_result[:max(100, self.context_limits.max_tool_output_chars - 500)],
                        "full_result_path": str(log_path.relative_to(self.workspace_path)),
                        "truncated": True,
                    })

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": serialized_result,
                    }
                )

            last_error = None
            next_response = None
            successful_next_input: list[Any] | None = None
            for attempt in range(1, self.context_limits.max_retries + 1):
                bounded_tool_outputs = self.context_guard.trim_function_call_outputs(
                    tool_outputs,
                    attempt=attempt,
                )
                next_input: list[Any] = [
                    *response_input_items,
                    *response.output,
                    *bounded_tool_outputs,
                ]

                next_input = self._compact_continuation(
                    next_input, bounded_input_items, scope, attempt, emit,
                )
                check_cancelled()
                try:
                    next_response = create_tool_response(self.client,
                        model=self.model,
                        instructions=instructions,
                        input=next_input,
                        tools=tools,
                        options=self.llm_options,
                        temperature=self.temperature,
                    )
                    successful_next_input = next_input
                    break
                except Exception as exc:
                    last_error = exc
                    if not self.context_guard.is_context_length_error(exc):
                        raise

            if next_response is None or successful_next_input is None:
                raise RuntimeError(
                    "Failed to continue model response after context trimming retries."
                ) from last_error

            response_input_items = successful_next_input
            response = next_response

        raise BudgetExhausted("Worker iteration budget reached; durable work can be resumed.")
























            
            
    def _compact_continuation(self, items, original, scope, attempt, emit):
        def serializable(item):
            if isinstance(item, dict):
                return item
            if hasattr(item, "model_dump"):
                return item.model_dump(exclude_none=True)
            return vars(item)
        size = len(json.dumps([serializable(i) for i in items], default=str))
        budget = max(2000, self.context_limits.max_input_chars // attempt)
        if size <= budget:
            return items
        # Restart only at a tool-round boundary: never retain orphaned call/output
        # pairs or stale reasoning. Full evidence is already persisted on disk.
        directory = Path(self.workspace_path) / ".agent" / "tool-results"
        directory.mkdir(parents=True, exist_ok=True)
        archive = directory / ("context-" + uuid.uuid4().hex + ".json")
        archive.write_text(json.dumps([serializable(i) for i in items], default=str, ensure_ascii=False), encoding="utf-8")
        state = TaskBoard(self.workspace_path, scope).summary()
        state["transcript"] = str(archive.relative_to(self.workspace_path))
        checkpoint = {
            "role": "user",
            "content": ("Continue the original task from this durable checkpoint. "
                        "Earlier tool rounds were archived in .agent/tool-results; "
                        "read relevant logs and task_board state as needed. Do not repeat side effects.\n"
                        + json.dumps(state, ensure_ascii=False)),
        }
        recent = [serializable(i) for i in items if
                  (i.get("type") if isinstance(i, dict) else getattr(i, "type", None)) == "function_call_output"]
        if recent:
            checkpoint["content"] += "\nLatest tool results: " + json.dumps(recent[-2:], default=str)[-budget // 3:]
        seed = {"role": "user", "content": str(original[-1].get("content", ""))[:budget // 3]}
        checkpoint["content"] = checkpoint["content"][:budget // 2]
        if emit:
            emit("context.compacted", {"agent": self.name, "previous_chars": size})
        return [seed, checkpoint]

    def chat_without_tools(self, messages: list[dict]) -> str:
        msgs = list(messages)
        request_messages = [
            {"role": "system", "content": self.system_message},
            *msgs,
        ]

        response = None
        last_error: Exception | None = None

        for attempt in range(1, self.context_limits.max_retries + 1):
            bounded_messages = self.context_guard.trim_messages(
                request_messages,
                attempt=attempt,
            )

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=bounded_messages,
                    **generation_options(self.llm_options, self.temperature),
                )
                break
            except Exception as exc:
                last_error = exc
                if not self.context_guard.is_context_length_error(exc):
                    raise

        if response is None:
            raise RuntimeError(
                "Failed to create completion after context trimming retries."
            ) from last_error

        message = response.choices[0].message
        # print(message)
        
        return message.content





    def _assistant_message_to_dict(self, message: Any) -> dict[str, Any]:
        
        result: dict[str, Any] = {
            "role": "assistant",
        }

        if message.content is not None:
            result["content"] = message.content

        if message.refusal is not None:
            result["refusal"] = message.refusal

        if message.tool_calls:
            result["tool_calls"] = [
                tool_call.model_dump(exclude_none=True)
                for tool_call in message.tool_calls
            ]

        return result
