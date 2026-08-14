"""Lightweight read-only helpers for populating GUI pickers (prompt files,
response schemas, existing sessions) from the shared data directory.

Kept separate from client/ (which is intentionally independent of the agent
package) since service/ already imports agent directly.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from agent.paths import DATA_ROOT
from agent.user_storage import user_storage_paths

import yaml

AGENT_ROOT = Path(__file__).resolve().parents[1] / "agent"
CONFIG_PATH = AGENT_ROOT / "config.yml"

with CONFIG_PATH.open("r", encoding="utf-8") as _f:
    _config = yaml.safe_load(_f)

RESOURCES_DIR = DATA_ROOT / _config["agents_resources"].split("/")[0]
PROMPTS_DIR = RESOURCES_DIR / "user_prompts"
SESSION_DIR = DATA_ROOT / _config["session"]
MEMORY_DIR = DATA_ROOT / _config["memory"]


def list_prompt_files() -> List[str]:
    if not PROMPTS_DIR.is_dir():
        return []
    return sorted(p.name for p in PROMPTS_DIR.glob("*.md") if p.is_file())


def read_prompt_file(name: str) -> str:
    path = (PROMPTS_DIR / name).resolve()
    if PROMPTS_DIR.resolve() not in path.parents or not path.is_file():
        raise FileNotFoundError(name)
    return path.read_text(encoding="utf-8")


def list_response_schemas() -> List[str]:
    if not RESOURCES_DIR.is_dir():
        return []
    return sorted(p.name for p in RESOURCES_DIR.glob("*.json") if p.is_file())


def list_sessions(username: str) -> List[Dict[str, Any]]:
    storage = user_storage_paths(username, session_folder=SESSION_DIR, memory_folder=MEMORY_DIR)
    session_dir = Path(storage.session_folder)
    if not session_dir.is_dir():
        return []

    sessions: List[Dict[str, Any]] = []
    for session_file in sorted(session_dir.glob("session_*.sqlite3")):
        session_id = session_file.stem.replace("session_", "")
        try:
            with sqlite3.connect(session_file) as connection:
                connection.row_factory = sqlite3.Row
                row = connection.execute(
                    "SELECT created_at, summary FROM sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
        except sqlite3.Error:
            continue

        sessions.append(
            {
                "id": session_id,
                "created_at": row["created_at"] if row else None,
                "summary": row["summary"] if row else None,
            }
        )

    sessions.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return sessions
