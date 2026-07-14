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

    model: str
    api_key: str
    base_url: str
    temperature: float
    
    client: Union[OpenAI, Any]



    def __init__(self, id, name, model, api_key, base_url, temperature, resources_path):
        self.id = id
        
        self.name = name
        self.resources_path = resources_path

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
                tools=tools
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
                        workspace=".",
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