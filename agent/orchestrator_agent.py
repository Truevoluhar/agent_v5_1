import json
from collections.abc import Iterable
from typing_extensions import Self
from typing import Any, Type, Literal, Optional, Union, TypeVar
from dataclasses import dataclass, asdict, is_dataclass

import uuid
from openai import OpenAI
from pydantic import BaseModel, Field, create_model, model_validator, ConfigDict

from agent.session import Session
from agent.generic_agent import GenericAgent
from agent.tools.tools_registry import get_tool_schemas, execute_registered_tool

ResponseT = TypeVar("ResponseT", bound=BaseModel)

class OrchestratorResponseBase(BaseModel):

    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "ask_user",
        "delegate_to_agent",
        "finish",
    ] = Field(
        description="Action the orchestrator should take."
    )

    description: str = Field(
        description="Short description of the task or result."
    )

    @model_validator(mode="after")
    def validate_agent_selection(self) -> Self:
        agent_name = getattr(self, "agent_name", None)

        if self.action == "delegate_to_agent":
            if agent_name is None:
                raise ValueError("agent_name is required when delegating task to agent")
        elif agent_name is not None:
            raise ValueError("agent_name must me null unless delegating task to agent")

        return self


def create_orchestrator_response(
        available_agents: Iterable[str]
    ) -> type[BaseModel]:
        agent_names = tuple(dict.fromkeys(available_agents))

        if not agent_names:
            raise ValueError("No agent available")

        AgentName = Literal.__getitem__(agent_names)

        return create_model(
            "OrchestratorResponse",
            __base__=OrchestratorResponseBase,
            agent_name = (
                Optional[AgentName],
                Field(
                    default=None,
                    description=(
                        "Must be one of the currently available agent names when delegating. Otherwise null."
                    )
                )
            )
        )


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
    
    client: Union[OpenAI, Any]

    available_agents: list[str]
    response_model: Type[BaseModel]



    def __init__(self, id, name, model, api_key, base_url, temperature, resources_path, workspace_path, available_agents):
        self.id = id
        
        self.name = name
        self.resources_path = resources_path
        self.workspace_path = workspace_path

        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature

        self.agentmd = self.load_agentmd(self.name)
        self.skillsmd = self.load_skillsmd(self.name)
        self.client = self.init_client()
        
        self.available_agents = list(
            dict.fromkeys(available_agents)
        )
        self.response_model = create_orchestrator_response(self.available_agents)

        self.system_message = self.create_system_message()



    def load_agentmd(self, agent_name: str) -> None:

        print(f"[{self.name}] Loading System Message ...")

        path = self.resources_path + "/" + agent_name + "/AGENT.md"
        with open(path, "r") as f:
            content = f.read()
            return content
        
    
    def load_skillsmd(self, agent_name: str) -> None:

        print(f"[{self.name}] Loading Skills Message ...")

        path = self.resources_path + "/" + agent_name + "/SKILLS.md"
        with open(path, "r") as f:
            content = f.read()
            return content
        
    
    def init_client(self) -> None:

        client_kwargs = { "api_key": self.api_key }
        
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = OpenAI(**client_kwargs)
        return client
    

    def create_system_message(self):

        sys_msg = ""

        sys_msg += self.agentmd
        sys_msg += self.skillsmd

        sys_msg += "\n\n AVAILABLE AGENTS \n"
        for ag in self.available_agents:
            sys_msg += f"OFFICIAL AGENT NAME: {ag}\n"
            ag_system_message = self.load_agentmd(ag)
            ag_skills = self.load_skillsmd(ag)
            sys_msg += ag_system_message
            sys_msg += ag_skills
        
        return sys_msg






    def chat(self, messages: list[dict]) -> str:
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            timeout=None
        )

        message = response.choices[0].message

        return message
    

    def chat_structured(
            self,
            messages: list[dict],
    ) -> BaseModel:

        
        def message_to_str(m):
            return json.dumps(m)
        
        request_messages = [
            { "role": "system", "content": self.system_message },
            { "role": "user", "content": message_to_str(messages) }
        ]

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=request_messages,
            response_format=self.response_model,
            temperature=self.temperature,
            reasoning_effort="medium"
        )

        message = completion.choices[0].message

        if message.refusal:
            raise RuntimeError(f"Model refused the request: {message.refusal}")

        if message.parsed is None:
            raise RuntimeError(
                f"Model response could not be parsed. Raw content: {message.content}"
            )

        parsed_response = message.parsed

        print(f"[{self.name}]: {parsed_response}")

        return parsed_response

    
    def chat_structured_with_tools(
        self,
        messages: list[dict[str, Any]],
        session: Session,
        response_model: type[ResponseT]
    ) -> ResponseT:
        tools = get_tool_schemas()

        request_messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": self.system_message,
            },
            *messages,
        ]

        max_tool_rounds = 10

        for _ in range(max_tool_rounds):
            # Use create(), not parse(), during tool execution.
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                temperature=self.temperature,
                timeout=None,
                tools=tools,
                tool_choice="auto",
            )

            message = completion.choices[0].message
            request_messages.append(message)
            session.add_message(message=self._assistant_message_to_dict(message))

            if message.refusal:
                raise RuntimeError(
                    f"Model refused the request: {message.refusal}"
                )

            if message.tool_calls:
                request_messages.append(
                    self._assistant_tool_message_to_dict(message)
                )

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name

                    try:
                        arguments = json.loads(
                            tool_call.function.arguments
                        )
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            f"Invalid arguments for tool {tool_name!r}: "
                            f"{tool_call.function.arguments!r}"
                        ) from exc

                    print(
                        f"[{self.name}]: "
                        f"Tool call: {tool_name}({arguments})"
                    )

                    tool_result = execute_registered_tool(
                        workspace=self.workspace_path,
                        tool_name=tool_name,
                        tool_input=arguments,
                    )

                    if is_dataclass(tool_result):
                        tool_payload = asdict(tool_result)
                    elif isinstance(tool_result, BaseModel):
                        tool_payload = tool_result.model_dump()
                    else:
                        tool_payload = tool_result

                    tool_response = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            tool_payload,
                            ensure_ascii=False,
                            default=str,
                        ),
                    }
                    request_messages.append(tool_response)
                    session.add_message(message=tool_response)

                continue

            # The model has stopped requesting tools.
            # Preserve its draft answer as context for final serialization.
            if message.content:

                request_messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                    }
                )
                session.add_message(
                    message={
                        "role": "assistant",
                        "content": message.content,
                    }
                )

            break

        else:
            raise RuntimeError(
                f"Model exceeded {max_tool_rounds} tool-calling rounds."
            )

        # Separate final call: tools are intentionally omitted.
        request_messages.append(
            {
                "role": "user",
                "content": (
                    "Return the final result as exactly one structured response "
                    "matching the required schema. Do not include commentary, "
                    "Markdown, or multiple JSON objects."
                ),
            }
        )

        final_completion = self.client.chat.completions.parse(
            model=self.model,
            messages=request_messages,
            response_format=response_model,
            temperature=self.temperature,
            timeout=None,
        )

        final_message = final_completion.choices[0].message

        if final_message.refusal:
            raise RuntimeError(
                f"Model refused the request: {final_message.refusal}"
            )

        if final_message.parsed is None:
            raise RuntimeError(
                "Final response could not be parsed. "
                f"Raw content: {final_message.content!r}"
            )

        parsed_response: ResponseT = final_message.parsed

        print(f"[{self.name}]: {parsed_response}")

        return parsed_response


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


    def _assistant_tool_message_to_dict(
        self,
        message: Any,
    ) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in message.tool_calls or []
            ],
        }


class CreatePlanResponse(BaseModel):
    is_plan_created: bool
    filename: str