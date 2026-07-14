import os
import json
import argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv
import questionary

from agent.test import run_tests

from agent.generic_agent import GenericAgent
from agent.orchestrator_agent import OrchestratorAgent, TestSessionItem
from agent.session import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = str(AGENT_ROOT / "config.yml")

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--initial_prompt", help="First prompt where you describe what you want to do with agent.")

    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory the agent can access."
    )
    parser.add_argument(
        "--interactive",
        choices=["true", "false"],
        default="false",
        help="Enable chat mode with agent(s)"
    )
    parser.add_argument(
        "--test",
        choices=["true", "false"],
        default="false",
        help="Pozenemo testno funkcijo namesto agentskega loopa"
    )
    
    
    args = parser.parse_args()

    # Naložimo okoljske spremenljivke iz .env datoteke
    load_dotenv()
    

    if args.test == "true":
        run_tests()
        return


    # CONFIG LOAD
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    
    


    agents_config = config["agents"]
    orchestrator_config = config['orchestrator_agent']
    agent_resources = str(PROJECT_ROOT / config['agents_resources'])


    
    # Ponudimo opcije za session
    if args.interactive == "true" and _check_existing_sessions(config['session']):
        options = [
            "Ustvari novo sejo",
            "Nalozi obstojeco sejo"
        ]
        

        option = questionary.select("Izberi moznost:", choices=options).ask()
        
        if option == "Nalozi obstojeco sejo":
            existing_sessions = _get_existing_sessions(config['session'])
            chosen_session = questionary.select("Izberi sejo: ", choices=existing_sessions).ask()

            session = Session(
                id=_get_id_for_existing_session(chosen_session),
                messages=_get_existing_session_messages(config['session'], chosen_session),
                session_folder=config['session'],
                workspace_folder=config['workspace'],
                memory_folder=config['memory']
            )
        else:
            # INSTANCIRAMO NOV SESSION
            session = Session(
                session_folder=config['session'],
                workspace_folder=config['workspace'],
                memory_folder=config['memory']
            )

    
    
    

    # INSTANCIRAMO GENERIČNE AGENTE
    agents: list[GenericAgent] = []
    for agent_id, agent_data in agents_config.items():
        print(f"[CLI] Loading Agent => ID: {agent_id}, NAME: {agent_data['name']}")
        agent = GenericAgent(
            id=agent_id,
            name=agent_data['name'],
            model=agent_data['model'],
            temperature=agent_data['temperature'],
            base_url=agent_data['base_url'],
            api_key=os.getenv(agent_data['api_key']),
            resources_path=agent_resources
        )
        agents.append(agent)


    
    # INSTANCIRAMO ORCHESTRATOR AGENTA, ki odloča o poteku
    available_agents = []
    for agent in agents:
        available_agents.append(agent.name)
    
    orchestrator_agent = OrchestratorAgent(
        id="orchestrator_agent",
        name=orchestrator_config['name'],
        model=orchestrator_config['model'],
        temperature=orchestrator_config['temperature'],
        base_url=orchestrator_config['base_url'],
        api_key=os.getenv(orchestrator_config['api_key']),
        resources_path=agent_resources,
        available_agents=available_agents
    )


    # Setup prvega sporocila
    messages = [
            { "role": "user", "content": args.initial_prompt }
    ]
    session.add_message(messages[0])

    

    # AGENT LOOP
    for step in range(config["max_steps"]):
        print(f"Running step {step} ...")
        
        

        
        orchestrator_response: TestSessionItem = orchestrator_agent.chat_structured(
            messages=session.messages,
            response_model=TestSessionItem,
        )
        
        session.add_message({ "role": "assistant", "content": orchestrator_response.description })

        if orchestrator_response.action == "delegate_to_agent":
            for agent in agents:
                if agent.name == orchestrator_response.agent_name:
                    agent_response = agent.chat(session.messages, session)

        if orchestrator_response.action == "ask_user":
            user_response = input("Respond to agent: ")
            session.add_message({ "role": "user", "content": user_response })

        if orchestrator_response.action == "finish":
            return


def _get_existing_sessions(sessions_path: str):
    folder = Path(sessions_path)
    
    if folder.exists() and folder.is_dir():
        folder_not_empty = any(folder.iterdir())

        if folder_not_empty:
            session_files = [
                path
                for path in folder.glob("session_*.jsonl")
                if path.is_file()
            ]

            if session_files:
                sessions = []
                for s in session_files:
                    s = str(s)
                    s = s.split("/")[1]
                    s = s.split(".")[0]
                    sessions.append(str(s))
                return sessions
                    
            else:
                print("Nobena obstojeca seja ne obstaja.")
        else:
            print("Nobena obstojeca seja ne obstaja.")
    else:
        print("Nobena obstojeca seja ne obstaja.")
        
        
        
def _check_existing_sessions(sessions_path: str) -> bool:
    folder = Path(sessions_path)
    
    if folder.exists() and folder.is_dir():
        folder_not_empty = any(folder.iterdir())

        if folder_not_empty:
            session_files = [
                path
                for path in folder.glob("session_*.jsonl")
                if path.is_file()
            ]

            if session_files:
                return True
                    
            else:
                return False
        else:
            return False
    else:
        return False
    
    
def _get_id_for_existing_session(session_name: str) -> str:
    return session_name.split("_")[1]


def _get_existing_session_messages(sessions_path: str, session_name: str) -> list[dict]:
    session_fullpath = f"{sessions_path}/{session_name}.jsonl"
    
    messages = []
    with open(session_fullpath, "r") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            
            if not line:
                continue
            
            try:
                messages.append(json.loads(line))
            except Exception as e:
                raise ValueError(
                    f"Invalid JSON on line {line_num}: {e}"
                ) from e
                
    return messages