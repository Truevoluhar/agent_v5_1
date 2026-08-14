"""Resolution of the shared data root (session/memory/resources/workspace).

The agent container never owns this data directly - it is a bind mount shared
with the independent client. Locally (outside Docker) it defaults to the
``data/`` directory at the repository root so the agent keeps working without
any container involved.
"""
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATA_ROOT = _REPO_ROOT / "data"

DATA_ROOT = Path(os.environ.get("AGENT_DATA_ROOT", str(_DEFAULT_DATA_ROOT))).resolve()
