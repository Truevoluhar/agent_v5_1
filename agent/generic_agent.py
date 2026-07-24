import json
from typing import Any, Union
from dataclasses import dataclass

from openai import OpenAI

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
    
    client: Union[OpenAI, Any]



    def __init__(self, id, name, model, api_key, base_url, temperature, resources_path, workspace_path):
        self.id = id
        
        self.name = name
        self.resources_path = resources_path
        self.workspace_path = workspace_path

        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature

        self.agentmd = self.load_agentmd()
        self.skillsmd = self.load_skillsmd()
        self.system_message = self.create_system_message()
        
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

        client_kwargs = { "api_key": self.api_key }
        
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = OpenAI(**client_kwargs)
        return client



    """
    def chat(self, messages: list[dict], session: Session) -> str:

        tools = get_tool_schemas()

        msgs = list(messages)

        request_messages = [
            {"role": "system", "content": self.system_message },
            *msgs
        ]
        
        print(request_messages)
        
        for _ in range(10):
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                temperature=self.temperature,
                timeout=None,
                tool_choice="auto",
                tools=tools,
                reasoning_effort="medium"
            )

            message = response.choices[0].message
            # print(message)

            request_messages.append(message)
            session.add_message(message=self._assistant_message_to_dict(message))
            
            
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    print(f"[{self.name}]: Tool call: {tool_name}")
                    tool_result = execute_registered_tool(
                        workspace=self.workspace_path,
                        tool_name=tool_name,
                        tool_input=arguments
                    )
                    tool_response = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            tool_result,
                            ensure_ascii=False,
                            default=str
                        )
                    }
                    
                    request_messages.append(tool_response)
                    session.add_message(tool_response)
                    
                continue
                    
            else:
                return message.content
    """


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


    def chat(self, messages: list[dict], session: Session) -> str:
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

        response = self.client.responses.create(
            model=self.model,
            instructions=self.system_message,
            input=input_items,
            tools=tools,
            tool_choice="auto",
            reasoning={
                "effort": "medium",
            },
        )

        for _ in range(100):
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

                return final_text

            tool_outputs: list[dict[str, Any]] = []

            for tool_call in tool_calls:
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

                    try:
                        tool_result = execute_registered_tool(
                            workspace=self.workspace_path,
                            tool_name=tool_name,
                            tool_input=arguments,
                        )
                    except Exception as exc:
                        # Return the error to the model so it can recover,
                        # select another tool, or explain the failure.
                        tool_result = {
                            "error": f"{type(exc).__name__}: {exc}"
                        }

                serialized_result = json.dumps(
                    tool_result,
                    ensure_ascii=False,
                    default=str,
                )

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": serialized_result,
                    }
                )

            # previous_response_id preserves the model output, including the
            # reasoning and function-call items, for the next tool-loop step.
            response = self.client.responses.create(
                model=self.model,
                instructions=self.system_message,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=tools,
                tool_choice="auto",
                reasoning={
                    "effort": "medium",
                },
            )

        raise RuntimeError("Maximum tool-call iterations reached.")
























            
            
    def chat_without_tools(self, messages: list[dict]) -> str:
        msgs = list(messages)

        request_messages = [
            {"role": "system", "content": self.system_message },
            *msgs
        ]
        print(request_messages)
        
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=request_messages,
            temperature=self.temperature,
            timeout=None,
        )

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