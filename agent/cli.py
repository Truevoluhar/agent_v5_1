import argparse
from pathlib import Path

import yaml

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
    

    args = parser.parse_args()


    # CONFIG LOAD
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print(str(config))

    agents_config = config["agents"]
    orchestrator_config = config['orchestrator_agent']
    agent_resources = str(PROJECT_ROOT / config['agents_resources' ])


    # INSTANCIRAMO NOV SESSION
    session = Session()

    

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
            api_key=agent_data['api_key'],
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
        api_key=orchestrator_config['api_key'],
        resources_path=agent_resources,
        available_agents=available_agents
    )


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
                    agent_response = agent.chat(session.messages)
                    session.add_message({ "role": "assistant", "content": agent_response })

        if orchestrator_response.action == "ask_user":
            user_response = input("Respond to agent: ")
            session.add_message({ "role": "user", "content": user_response })

        if orchestrator_response.action == "finish":
            return

        """
        for agent in agents:
            print(f"Available agent: {agent.name}: {agent.id}")
        
        
        planner = agents[0]

        messages = [
            {"role": "system", "content": planner.system_message},
            {"role": "user", "content": "Whats 2+2?"}
        ]

        response = planner.chat(messages=messages)
        print(response)
        """
        