import os
import json
import argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv
import questionary

from agent.test import run_tests

from agent.generic_agent import GenericAgent
from agent.orchestrator_agent import OrchestratorAgent
from agent.session import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = str(AGENT_ROOT / "config.yml")
DEFAULT_PLAN_FILENAME = "PLAN.md"
MAX_PLAN_CONTEXT_CHARS = 12_000


def _read_active_plan_context(workspace_path: str, filename: str = DEFAULT_PLAN_FILENAME) -> tuple[str | None, dict]:
    plan_path = Path(workspace_path) / filename
    if not plan_path.exists():
        return None, {"exists": False, "path": str(plan_path)}

    content = plan_path.read_text(encoding="utf-8")
    metadata = {
        "exists": True,
        "path": str(plan_path),
        "chars": len(content),
        "truncated": False,
    }

    if len(content) > MAX_PLAN_CONTEXT_CHARS:
        metadata["truncated"] = True
        content = content[:MAX_PLAN_CONTEXT_CHARS] + "\n\n[TRUNCATED PLAN CONTEXT]"

    return content, metadata


def _find_agent_by_name(agents: list[GenericAgent], agent_name: str) -> GenericAgent | None:
    for agent in agents:
        if agent.name == agent_name:
            return agent
    return None


def _planner_name(agents: list[GenericAgent]) -> str | None:
    planner_agent = _find_agent_by_name(agents, "PLANNER")
    return planner_agent.name if planner_agent is not None else None



def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--initial_prompt", help="First prompt where you describe what you want to do with agent.", required=True)

    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory the agent can access.",
        required=True
    )
    parser.add_argument(
        "--interactive",
        choices=["true", "false"],
        default="false",
        help="Enable chat mode with agent(s)",
        required=True
    )
    parser.add_argument(
        "--test",
        choices=["true", "false"],
        default="false",
        help="Pozenemo testno funkcijo namesto agentskega loopa",
        required=True
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
        
    
    # Parsamo user prompt
    # Če se začne z file=, preberemo iz datoteke
    if args.initial_prompt.startswith("file="):
        print("Berem uporabnikov prompt iz datoteke ...")
        try:
            filename = args.initial_prompt.split("=")[1]
            with open(f"./resources/user_prompts/{filename}", "r", encoding="utf-8") as f:
                prompt_content = f.read()
            args.initial_prompt = prompt_content
        except Exception as e:
            print(e)
            return

    

    agents_config = config["agents"]
    orchestrator_config = config['orchestrator_agent']
    agent_resources = str(PROJECT_ROOT / config['agents_resources'])

    # Nastavimo workspace folder
    if config["workspace"]:
        AGENT_WORKSPACE = str(Path(PROJECT_ROOT / config["workspace"]))
        Path(f"{AGENT_WORKSPACE}/plan").mkdir(parents=True, exist_ok=True)
    else:
        AGENT_WORKSPACE = str(Path(PROJECT_ROOT))
        Path(f"{AGENT_WORKSPACE}/plan").mkdir(parents=True, exist_ok=True)


    
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
            resources_path=agent_resources,
            workspace_path=AGENT_WORKSPACE
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
        workspace_path=AGENT_WORKSPACE,
        available_agents=available_agents
    )


    # Setup prvega sporocila
    messages = [
            { "role": "user", "content": args.initial_prompt }
    ]
    session.add_message(messages[0])


    





    ##############
    #            #
    # AGENT LOOP #
    #            #
    ##############

    for step in range(config["max_steps"]):
        print(f"Running step {step} ...")

        recent_query = next(
            (
                message.get("content")
                for message in reversed(session.messages)
                if message.get("role") == "user" and message.get("content")
            ),
            None,
        )
        historical_context = []
        if recent_query:
            historical_context = session.hybrid_retrieve(query=recent_query, limit=3)

        plan_text, _ = _read_active_plan_context(AGENT_WORKSPACE)

        orchestrator_messages = session.get_bounded_context(max_recent_messages=12)
        if plan_text is not None:
            plan_context_line = (
                "Active plan (source of truth). Follow this plan and update it instead of creating a separate one.\n\n"
                f"{plan_text}"
            )
            orchestrator_messages.insert(
                0,
                {
                    "role": "system",
                    "content": plan_context_line,
                },
            )
        else:
            orchestrator_messages.insert(
                0,
                {
                    "role": "system",
                    "content": (
                        "No active plan file found at PLAN.md. "
                        "Delegate to PLANNER to create one before substantial implementation tasks."
                    ),
                },
            )

        if historical_context:
            orchestrator_messages.insert(
                0,
                {
                    "role": "system",
                    "content": (
                        "Historical memory evidence from the current session: "
                        f"{json.dumps(historical_context, ensure_ascii=False, default=str)}"
                    ),
                },
            )

        orchestrator_response = orchestrator_agent.chat_structured(
            messages=orchestrator_messages,
        )

        session.add_message({"role": "assistant", "content": orchestrator_response.description})

        if orchestrator_response.action == "delegate_to_agent":
            delegated_name = orchestrator_response.agent_name
            planner = _planner_name(agents)

            # Guardrail: when plan is missing, force a planner pass first.
            if plan_text is None and planner is not None and delegated_name != planner:
                delegated_name = planner
                session.add_message(
                    {
                        "role": "system",
                        "content": (
                            "Delegation overridden to PLANNER because no active PLAN.md exists yet. "
                            "Create/refresh PLAN.md first."
                        ),
                    }
                )

            delegated_agent = _find_agent_by_name(agents, delegated_name)
            if delegated_agent is not None:
                agent_messages = session.get_bounded_context(max_recent_messages=12)

                if plan_text is not None:
                    agent_messages.insert(
                        0,
                        {
                            "role": "system",
                            "content": (
                                "Execution must follow active PLAN.md. "
                                "If work changes scope, update PLAN.md first, then continue."
                            ),
                        },
                    )

                delegated_agent.chat(agent_messages, session)

        if orchestrator_response.action == "ask_user":
            user_response = input("Respond to agent: ")
            session.add_message({"role": "user", "content": user_response})

        if orchestrator_response.action == "finish":
            return







def _get_existing_sessions(sessions_path: str):
    folder = Path(sessions_path)

    if folder.exists() and folder.is_dir():
        folder_not_empty = any(folder.iterdir())

        if folder_not_empty:
            session_files = [
                path
                for path in folder.glob("session_*.sqlite3")
                if path.is_file()
            ]
            session_files.extend(
                [
                    path
                    for path in folder.glob("session_*.jsonl")
                    if path.is_file()
                ]
            )

            if session_files:
                sessions = []
                for s in session_files:
                    sessions.append(str(s.stem))
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
                for path in folder.glob("session_*.sqlite3")
                if path.is_file()
            ]
            session_files.extend(
                [
                    path
                    for path in folder.glob("session_*.jsonl")
                    if path.is_file()
                ]
            )

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