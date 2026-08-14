import os
import json
from pathlib import Path

import yaml

from agent.generic_agent import GenericAgent
from agent.session import Session
from agent.paths import DATA_ROOT


AGENT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = str(AGENT_ROOT / "config.yml")


def run_tests():
    _compact_memory()
    
    
def _compact_memory():
    print("[TEST] COMPACT MEMORY")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    sessions_path = DATA_ROOT / config['session']
    session_file = "session_46550ce6-cd3e-492d-967f-7568ebd776b1.jsonl"
    
    memory = []
    with open(f"{sessions_path}/{session_file}", "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            
            if line is None:
                continue
                
            try:
                memory.append(json.loads(line))
            except Exception as e:
                raise TypeError(e)
            
    memory_agent_config = config['memory_agent']
    agent_resources = str(DATA_ROOT / config['agents_resources'])
    
    memory_agent = GenericAgent(
        id="memory_agent",
        name=memory_agent_config['name'],
        model=memory_agent_config['model'],
        api_key=os.getenv(memory_agent_config['api_key']),
        base_url=memory_agent_config['base_url'],
        temperature=memory_agent_config['temperature'],
        resources_path=agent_resources
    )
    
    session_id = session_file.split("_")[1]
    session_id = session_id.split(".")[0]
    
    session = Session(
        id=session_id,
        messages=memory,
        memory_folder=str(DATA_ROOT / config['memory']),
        workspace_folder=str(DATA_ROOT / config['workspace']),
        session_folder=str(DATA_ROOT / config['session']),
    )
    
    memory.append(
        {"role": "user", "content": "Create a summary of provided messages. Summary should not be longer than 400 words."}
    )
    
    memory_agent_response = memory_agent.chat_without_tools(messages=memory)
    print(str(memory_agent_response))
    
    
    
    
    
    