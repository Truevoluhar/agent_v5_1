"""Resolution of the shared data root (session/memory/resources/workspace).

The client is an independent container/process from the agent. Both only
agree on where the shared bind mount lives; they share no Python code. This
module intentionally mirrors ``agent/paths.py`` without importing it.
"""
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATA_ROOT = _REPO_ROOT / "data"

DATA_ROOT = Path(os.environ.get("AGENT_DATA_ROOT", str(_DEFAULT_DATA_ROOT))).resolve()

SESSION_DIR = DATA_ROOT / "session"
MEMORY_DIR = DATA_ROOT / "memory"
WORKSPACE_DIR = DATA_ROOT / "agent_workspace"
RESOURCES_DIR = DATA_ROOT / "resources"
