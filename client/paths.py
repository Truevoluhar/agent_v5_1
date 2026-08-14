"""Shared filesystem root resolution for the client.

The client is a fully independent program from the agent. It never imports
agent code - it only reads/writes the same bind-mounted data directories
(resources/session/memory/agent_workspace) that the agent uses, so both
sides can exchange data purely through the filesystem.
"""

import os
from pathlib import Path

CLIENT_ROOT = Path(__file__).resolve().parent
# When run outside Docker, default to the repository root (sibling of agent/)
# so the client works out of the box against the existing local folders.
DEFAULT_LOCAL_ROOT = CLIENT_ROOT.parent

SHARED_ROOT_ENV_VAR = "CLIENT_SHARED_ROOT"


def shared_root() -> Path:
    return Path(os.environ.get(SHARED_ROOT_ENV_VAR, str(DEFAULT_LOCAL_ROOT))).resolve()
