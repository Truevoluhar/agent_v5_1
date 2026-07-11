import json
from typing import Any
from dataclasses import dataclass

from openai import OpenAI

from agent.tools.tools_registry import get_tool_schemas, execute_registered_tool


        

class GenericAgent:

    id: int

    name: str
    system_message: str
    skills: str
    resources_path: str

    model: str
    api_key: str
    base_url: str
    temperature: float
    
    client: OpenAI | Any



    def __init__(self, id, name, model, api_key, base_url, temperature, resources_path):
        self.id = id
        
        self.name = name
        self.resources_path = resources_path

        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature

        self.system_message = self.load_system_message()
        self.skills = self.load_skills()
        self.client = self.init_client()



    def load_system_message(self) -> None:

        print(f"[Agent] Loading System Message ...")

        path = self.resources_path + "/" + self.name + "/AGENT.md"
        with open(path, "r") as f:
            content = f.read()
            return content
        
    
    def load_skills(self) -> None:

        print(f"[Agent] Loading Skills Message ...")

        path = self.resources_path + "/" + self.name + "/AGENT.md"
        with open(path, "r") as f:
            content = f.read()
            return content
        
    
    def init_client(self) -> None:

        client_kwargs = { "api_key": self.api_key }
        
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = OpenAI(**client_kwargs)
        return client




    def chat(self, messages: list[dict]) -> str:

        tools = get_tool_schemas()

        msgs = list(messages)

        request_messages = [
            {"role": "system", "content": self.system_message },
            *msgs
        ]
        
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

                    request_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            tool_result,
                            ensure_ascii=False,
                            default=str
                        )
                    })
                continue
                    
            else:
                
                return message.content

