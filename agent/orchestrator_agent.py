import json
from typing import Any, Type, Literal, Optional, Union
from dataclasses import dataclass

import uuid
from openai import OpenAI
from pydantic import BaseModel, Field

from agent.generic_agent import GenericAgent



class TestSessionItem(BaseModel):
    action: Literal[
        "ask_user",
        "delegate_to_agent",
        "finish"
    ] = Field(description="List of available actions")
    description: str = Field(description="Short description of a task")
    agent_name: Optional[str] = Field(description="Official agent name")


       

class OrchestratorAgent:

    id: int

    name: str
    system_message: str
    agentmd: str
    skillsmd: str
    resources_path: str

    model: str
    api_key: str
    base_url: str
    temperature: float
    
    client: Union[OpenAI, Any]

    available_agents: list[str]



    def __init__(self, id, name, model, api_key, base_url, temperature, resources_path, available_agents):
        self.id = id
        
        self.name = name
        self.resources_path = resources_path

        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature

        self.agentmd = self.load_agentmd(self.name)
        self.skillsmd = self.load_skillsmd(self.name)
        self.client = self.init_client()
        
        self.available_agents = available_agents

        self.system_message = self.create_system_message()



    def load_agentmd(self, agent_name: str) -> None:

        print(f"[{self.name}] Loading System Message ...")

        path = self.resources_path + "/" + agent_name + "/AGENT.md"
        with open(path, "r") as f:
            content = f.read()
            return content
        
    
    def load_skillsmd(self, agent_name: str) -> None:

        print(f"[{self.name}] Loading Skills Message ...")

        path = self.resources_path + "/" + agent_name + "/AGENT.md"
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
            response_model: "Type[BaseModel]",
    ):
        
        def message_to_str(m):
            return json.dumps(m)
        
        request_messages = [
            { "role": "system", "content": self.system_message },
            { "role": "user", "content": message_to_str(messages) }
        ]

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=request_messages,
            response_format=response_model,
            temperature=self.temperature
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

    




    

class CreatePlanResponse(BaseModel):
    is_plan_created: bool
    filename: str