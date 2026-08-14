"""Per-user storage path helper, duplicated from agent/user_storage.py.

The client is an independent container from the agent and shares no Python
code with it - both only agree on the layout of the bind-mounted data
directory.
"""
import re
from dataclasses import dataclass
from pathlib import Path


_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,127}")


@dataclass(frozen=True)
class UserStoragePaths:
    session_folder: str
    memory_folder: str


def user_storage_paths(
    username: str,
    *,
    session_folder: str | Path,
    memory_folder: str | Path,
) -> UserStoragePaths:
    """Return isolated storage locations for a validated username."""
    if not isinstance(username, str) or not _USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "username must be 1-128 characters using letters, numbers, '.', '_', '-', or '@'"
        )

    return UserStoragePaths(
        session_folder=str(Path(session_folder) / username),
        memory_folder=str(Path(memory_folder) / username),
    )
