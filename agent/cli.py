import argparse
import json
import sqlite3
from pathlib import Path

import yaml
from dotenv import load_dotenv
import questionary

from agent.test import run_tests
from agent.events import ConsoleEventSink
from agent.paths import DATA_ROOT
from agent.runner import AgentRunner, RunRequest
from agent.user_storage import user_storage_paths


AGENT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = str(AGENT_ROOT / "config.yml")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--initial_prompt", help="First prompt where you describe what you want to do with agent.", required=True)
    parser.add_argument(
        "--username",
        required=True,
        help="Username that owns this user's sessions and memory.",
    )

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
    parser.add_argument(
        "--response-schema",
        help="Path to a JSON schema file or inline JSON schema for the final response agent.",
        default=None,
    )
    parser.add_argument(
        "--max-context-chars",
        type=int,
        default=None,
        help=(
            "Optional global upper bound for model input character budget. "
            "If provided, it overrides context_limits.max_input_chars from config."
        ),
    )

    args = parser.parse_args()

    # Naložimo okoljske spremenljivke iz .env datoteke
    load_dotenv()

    if args.test == "true":
        run_tests()
        return

    # CONFIG LOAD (only needed here to list/select existing sessions before delegating to AgentRunner)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    try:
        user_storage = user_storage_paths(
            args.username,
            session_folder=DATA_ROOT / config["session"],
            memory_folder=DATA_ROOT / config["memory"],
        )
    except ValueError as exc:
        parser.error(str(exc))

    # Parsamo user prompt
    # Če se začne z file=, preberemo iz datoteke
    initial_prompt = args.initial_prompt
    if initial_prompt.startswith("file="):
        print("Berem uporabnikov prompt iz datoteke ...")
        try:
            filename = initial_prompt.split("=")[1]
            with open(DATA_ROOT / "resources" / "user_prompts" / filename, "r", encoding="utf-8") as f:
                initial_prompt = f.read()
        except Exception as e:
            print(e)
            return

    # Ponudimo opcije za session
    session_id = None
    if args.interactive == "true" and _check_existing_sessions(user_storage.session_folder):
        options = [
            "Ustvari novo sejo",
            "Nalozi obstojeco sejo"
        ]

        option = questionary.select("Izberi moznost:", choices=options).ask()

        if option == "Nalozi obstojeco sejo":
            existing_sessions = _get_existing_sessions(user_storage.session_folder)
            session_id = questionary.select("Izberi sejo: ", choices=existing_sessions).ask()

    request = RunRequest(
        username=args.username,
        prompt=initial_prompt,
        workspace=args.workspace,
        session_id=session_id,
        response_schema=args.response_schema,
        max_context_chars=args.max_context_chars,
    )

    runner = AgentRunner(config_path=CONFIG_PATH)
    result = runner.run(
        request,
        emit=ConsoleEventSink(),
        wait_for_input=lambda question: input(f"{question}\nRespond to agent: "),
    )

    if result.status == "failed":
        print(f"[CLI] Run failed: {result.error}")
    elif result.final_response is not None:
        print(result.final_response.model_dump_json(indent=2))


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
                for session_file in session_files:
                    session_id = session_file.stem.removeprefix("session_")
                    session_name = _get_session_name(session_file, session_id)
                    sessions.append(questionary.Choice(f"{session_name} ({session_id[:8]})", value=session_id))
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


def _get_session_name(session_file: Path, session_id: str) -> str:
    if session_file.suffix != ".sqlite3":
        return "New chat"

    try:
        with sqlite3.connect(session_file) as connection:
            row = connection.execute(
                "SELECT name FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
    except Exception:
        return "New chat"

    return row[0] if row and row[0] else "New chat"


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