"""Independent client for the agent's shared bind mount.

This program never talks to the agent process directly - it only reads and
writes files inside the same shared data root (resources/, session/,
memory/, agent_workspace/) that the agent container has mounted. That
shared folder is the single point of contact between the two programs:

    AGENT  <-->  BIND MOUNT (shared data root)  <-->  CLIENT

Usage examples:
    python -m client.cli sessions
    python -m client.cli show <session_id>
    python -m client.cli ls agent_workspace
    python -m client.cli cat agent_workspace/PLAN.md
    python -m client.cli write agent_workspace/notes.txt --content "hello"
    python -m client.cli rm agent_workspace/notes.txt
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any

from client.paths import shared_root


def _resolve(relative_path: str) -> Path:
    """Resolve a user-supplied path against the shared root, refusing to
    escape outside of it."""
    root = shared_root().resolve()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Path '{relative_path}' escapes the shared root")
    return target


def _session_dir(config_session_subdir: str = "session") -> Path:
    return _resolve(config_session_subdir)


def cmd_sessions(args: argparse.Namespace) -> int:
    session_dir = _session_dir(args.session_dir)
    if not session_dir.exists():
        print(f"No session directory at {session_dir}")
        return 0

    rows: list[dict[str, Any]] = []
    for session_file in sorted(session_dir.glob("session_*.sqlite3")):
        session_id = session_file.stem.replace("session_", "")
        try:
            with sqlite3.connect(session_file) as connection:
                connection.row_factory = sqlite3.Row
                session_row = connection.execute(
                    "SELECT created_at, summary FROM sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
                count_row = connection.execute(
                    "SELECT COUNT(*) AS count FROM messages WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            print(f"[skip] {session_file.name}: {exc}", file=sys.stderr)
            continue

        rows.append(
            {
                "id": session_id,
                "created_at": session_row["created_at"] if session_row else None,
                "summary": session_row["summary"] if session_row else None,
                "message_count": count_row["count"] if count_row else 0,
            }
        )

    for row in sorted(rows, key=lambda item: item["created_at"] or "", reverse=True):
        print(f"{row['id']}  created={row['created_at']}  messages={row['message_count']}  summary={row['summary']}")

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    session_dir = _session_dir(args.session_dir)
    db_path = session_dir / f"session_{args.session_id}.sqlite3"
    if not db_path.exists():
        print(f"No such session: {db_path}", file=sys.stderr)
        return 1

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        query = "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id ASC"
        if args.limit:
            query += f" LIMIT {int(args.limit)}"
        cursor = connection.execute(query, (args.session_id,))
        for row in cursor.fetchall():
            print(f"[{row['created_at']}] {row['role']}: {row['content']}")

    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    target = _resolve(args.path)
    if not target.exists():
        print(f"No such path: {target}", file=sys.stderr)
        return 1

    if target.is_file():
        print(target.name)
        return 0

    for entry in sorted(target.iterdir()):
        suffix = "/" if entry.is_dir() else ""
        print(f"{entry.name}{suffix}")

    return 0


def cmd_cat(args: argparse.Namespace) -> int:
    target = _resolve(args.path)
    if not target.is_file():
        print(f"No such file: {target}", file=sys.stderr)
        return 1

    print(target.read_text(encoding="utf-8"))
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    target = _resolve(args.path)
    target.parent.mkdir(parents=True, exist_ok=True)

    content = args.content
    if content is None:
        content = sys.stdin.read()

    mode = "a" if args.append else "w"
    with target.open(mode, encoding="utf-8") as f:
        f.write(content)

    print(f"Wrote {len(content)} chars to {target}")
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    target = _resolve(args.path)
    if not target.exists():
        print(f"No such path: {target}", file=sys.stderr)
        return 1

    if target.is_dir():
        if not args.recursive:
            print(f"{target} is a directory, use --recursive to remove it", file=sys.stderr)
            return 1
        shutil.rmtree(target)
    else:
        target.unlink()

    print(f"Removed {target}")
    return 0


def cmd_mkdir(args: argparse.Namespace) -> int:
    target = _resolve(args.path)
    target.mkdir(parents=True, exist_ok=True)
    print(f"Created {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentv5-client",
        description="Inspect and manipulate the agent's shared data directory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sessions_parser = subparsers.add_parser("sessions", help="List available sessions")
    sessions_parser.add_argument("--session-dir", default="session")
    sessions_parser.set_defaults(func=cmd_sessions)

    show_parser = subparsers.add_parser("show", help="Show messages for a session")
    show_parser.add_argument("session_id")
    show_parser.add_argument("--session-dir", default="session")
    show_parser.add_argument("--limit", type=int, default=None)
    show_parser.set_defaults(func=cmd_show)

    ls_parser = subparsers.add_parser("ls", help="List a path inside the shared root")
    ls_parser.add_argument("path", nargs="?", default=".")
    ls_parser.set_defaults(func=cmd_ls)

    cat_parser = subparsers.add_parser("cat", help="Print a file inside the shared root")
    cat_parser.add_argument("path")
    cat_parser.set_defaults(func=cmd_cat)

    write_parser = subparsers.add_parser("write", help="Write/append a file inside the shared root")
    write_parser.add_argument("path")
    write_parser.add_argument("--content", default=None, help="Content to write. Reads stdin if omitted.")
    write_parser.add_argument("--append", action="store_true")
    write_parser.set_defaults(func=cmd_write)

    rm_parser = subparsers.add_parser("rm", help="Remove a file or directory inside the shared root")
    rm_parser.add_argument("path")
    rm_parser.add_argument("--recursive", action="store_true")
    rm_parser.set_defaults(func=cmd_rm)

    mkdir_parser = subparsers.add_parser("mkdir", help="Create a directory inside the shared root")
    mkdir_parser.add_argument("path")
    mkdir_parser.set_defaults(func=cmd_mkdir)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
