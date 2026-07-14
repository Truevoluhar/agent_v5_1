import os
import uuid
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

class Session:

    id: str
    session_folder : str
    workspace_folder: str
    messages: list[dict]

    def __init__(self, 
            session_folder: str, 
            workspace_folder: str, 
            memory_folder: str,
            id: str = None,
            messages: list[dict] = None
            ):

        self.id = id if id is not None else str(uuid.uuid4())
        self.messages = messages if messages is not None else []
        
        self.session_folder = session_folder
        self.workspace_folder = workspace_folder
        self.memory_folder = memory_folder
        
        if id == None and messages == None:
            self.create_session_folder()
            self.create_workspace_folder()
            self.create_folder(memory_folder)
            
            self.create_session_jsonl(session_folder)
        




    def create_session_jsonl(self, session_folder: str):
        open(f"{session_folder}/session_{self.id}.jsonl", "x")


    def add_message(self, message: Dict[str, Any]) -> None:
        self.messages.append(message)

        session_path = Path(
            self.session_folder,
            f"session_{self.id}.jsonl",
        )

        with session_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False, default=str))
            f.write("\n")


    def get_messages_for_agent(self):
        None

    
    def create_workspace_folder(self):
        try:
            os.mkdir(self.workspace_folder)
        except Exception as e:
            print(e)
            
    def create_session_folder(self):
        try:
            os.mkdir(self.session_folder)
        except Exception as e:
            print(e)
            
    def create_folder(self, folder):
        try:
            os.mkdir(folder)
        except Exception as e:
            print(e)
            
            
    def compact_memory(self):
        # DEBUG dolzina spomina
        """
        with open(f"{config['session']}/session_{session.id}.jsonl", "r") as f:
            session_length = len(str(f.read()))
            print(f"SESSION LENGTH: {session_length}")
            
            if session_length > 5000:
                f.seek(0)
                memory = []
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    try:
                        memory.append(json.loads(line))
                    except Exception as e:
                        raise ValueError(
                            f"Invalid JSON on line {line_num}: {e}"
                        ) from e
                
                memory_agent = GenericAgent(
                    id="memory_agent",
                    name="MEMORY",
                    model="gpt-4.1-mini",
                    base_url="https://api.openai.com/v1",
                    api_key=os.getenv(orchestrator_config['api_key']),
                    temperature=0.2,
                    resources_path=agent_resources
                )
                
                memory_agent_response = memory_agent.chat(
                    memory,
                    session
                )
                
                print(str(memory_agent_response))
        """