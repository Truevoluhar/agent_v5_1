"""Shared filesystem root resolution.

The agent runs as an independent container. Data that lives outside of the
agent program itself (resources, session transcripts, semantic memory,
agent workspace) is provided through a bind mount. Locally (outside Docker)
this defaults to the repository root so existing dev workflows keep working
unchanged.
"""

import os
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = AGENT_ROOT.parent

SHARED_ROOT_ENV_VAR = "AGENT_SHARED_ROOT"


def shared_root() -> Path:
    """Root directory containing the externally mounted data folders
    (resources/session/memory/agent_workspace). Override with the
    AGENT_SHARED_ROOT environment variable, e.g. /shared inside Docker."""
    return Path(os.environ.get(SHARED_ROOT_ENV_VAR, str(PROJECT_ROOT))).resolve()


def resolve_shared_path(relative_path: str) -> Path:
    return shared_root() / relative_path
