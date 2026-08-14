"""Independent CLI for manipulating the shared bind-mounted data directory.

Talks only to the filesystem under DATA_ROOT - no dependency on the agent
package. Run with `agentv5-client <command> ...` or `python -m client.cli`.
"""
import argparse
import json
import sys
from pathlib import Path

from client.paths import DATA_ROOT, MEMORY_DIR, RESOURCES_DIR, SESSION_DIR, WORKSPACE_DIR
from client import sessions as sessions_ops
from client.user_storage import user_storage_paths
from client import fsops

_ROOTS = {
    "session": SESSION_DIR,
    "memory": MEMORY_DIR,
    "workspace": WORKSPACE_DIR,
    "resources": RESOURCES_DIR,
}


def _user_session_dir(username: str) -> Path:
    storage = user_storage_paths(username, session_folder=SESSION_DIR, memory_folder=MEMORY_DIR)
    return Path(storage.session_folder)


def _cmd_sessions_list(args: argparse.Namespace) -> None:
    print(json.dumps(sessions_ops.list_sessions(_user_session_dir(args.username)), indent=2))


def _cmd_sessions_create(args: argparse.Namespace) -> None:
    session_id = sessions_ops.create_session(_user_session_dir(args.username), args.session_id)
    print(session_id)


def _cmd_sessions_show(args: argparse.Namespace) -> None:
    print(json.dumps(sessions_ops.read_session_messages(_user_session_dir(args.username), args.session_id), indent=2))


def _cmd_sessions_delete(args: argparse.Namespace) -> None:
    deleted = sessions_ops.delete_session(_user_session_dir(args.username), args.session_id)
    print("deleted" if deleted else "not found")


def _cmd_sessions_set_summary(args: argparse.Namespace) -> None:
    updated = sessions_ops.set_summary(_user_session_dir(args.username), args.session_id, args.summary)
    print("updated" if updated else "not found")


def _cmd_messages_add(args: argparse.Namespace) -> None:
    content = sys.stdin.read() if args.content is None else args.content
    message_id = sessions_ops.add_message(_user_session_dir(args.username), args.session_id, args.role, content)
    print(message_id)


def _cmd_messages_update(args: argparse.Namespace) -> None:
    content = sys.stdin.read() if args.content is None else args.content
    updated = sessions_ops.update_message(_user_session_dir(args.username), args.session_id, args.message_id, content)
    print("updated" if updated else "not found")


def _cmd_messages_delete(args: argparse.Namespace) -> None:
    deleted = sessions_ops.delete_message(_user_session_dir(args.username), args.session_id, args.message_id)
    print("deleted" if deleted else "not found")


def _cmd_fs_ls(args: argparse.Namespace) -> None:
    root = _ROOTS[args.root]
    print(json.dumps(fsops.list_files(root, args.path), indent=2))


def _cmd_fs_cat(args: argparse.Namespace) -> None:
    root = _ROOTS[args.root]
    sys.stdout.write(fsops.read_file(root, args.path))


def _cmd_fs_write(args: argparse.Namespace) -> None:
    root = _ROOTS[args.root]
    content = sys.stdin.read() if args.content is None else args.content
    fsops.write_file(root, args.path, content)
    print("written")


def _cmd_fs_upload(args: argparse.Namespace) -> None:
    root = _ROOTS[args.root]
    data = Path(args.local_file).read_bytes()
    fsops.write_file_bytes(root, args.path, data)
    print("uploaded")


def _cmd_fs_mkdir(args: argparse.Namespace) -> None:
    root = _ROOTS[args.root]
    fsops.make_dir(root, args.path)
    print("created")


def _cmd_fs_mv(args: argparse.Namespace) -> None:
    root = _ROOTS[args.root]
    fsops.move(root, args.src, args.dst)
    print("moved")


def _cmd_fs_rm(args: argparse.Namespace) -> None:
    root = _ROOTS[args.root]
    removed = fsops.delete_file(root, args.path, recursive=args.recursive)
    print("removed" if removed else "not found")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentv5-client", description="Manipulate the shared agent data directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("sessions-list", help="List sessions for a user.")
    p.add_argument("--username", required=True)
    p.set_defaults(func=_cmd_sessions_list)

    p = subparsers.add_parser("sessions-create", help="Create a new empty session.")
    p.add_argument("--username", required=True)
    p.add_argument("--session-id", default=None, help="Optional explicit session id (random uuid by default).")
    p.set_defaults(func=_cmd_sessions_create)

    p = subparsers.add_parser("sessions-show", help="Show messages for a session.")
    p.add_argument("--username", required=True)
    p.add_argument("--session-id", required=True)
    p.set_defaults(func=_cmd_sessions_show)

    p = subparsers.add_parser("sessions-delete", help="Delete a session's database.")
    p.add_argument("--username", required=True)
    p.add_argument("--session-id", required=True)
    p.set_defaults(func=_cmd_sessions_delete)

    p = subparsers.add_parser("sessions-set-summary", help="Set a session's summary text.")
    p.add_argument("--username", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--summary", required=True)
    p.set_defaults(func=_cmd_sessions_set_summary)

    p = subparsers.add_parser("messages-add", help="Append a message to a session.")
    p.add_argument("--username", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--content", default=None, help="Reads stdin if omitted.")
    p.set_defaults(func=_cmd_messages_add)

    p = subparsers.add_parser("messages-update", help="Edit an existing message's content.")
    p.add_argument("--username", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--message-id", type=int, required=True)
    p.add_argument("--content", default=None, help="Reads stdin if omitted.")
    p.set_defaults(func=_cmd_messages_update)

    p = subparsers.add_parser("messages-delete", help="Delete a single message from a session.")
    p.add_argument("--username", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--message-id", type=int, required=True)
    p.set_defaults(func=_cmd_messages_delete)

    p = subparsers.add_parser("ls", help="List files under a shared root (session/memory/workspace/resources).")
    p.add_argument("--root", choices=list(_ROOTS), required=True)
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=_cmd_fs_ls)

    p = subparsers.add_parser("cat", help="Print a file's contents.")
    p.add_argument("--root", choices=list(_ROOTS), required=True)
    p.add_argument("path")
    p.set_defaults(func=_cmd_fs_cat)

    p = subparsers.add_parser("write", help="Write a text file (reads stdin if --content is omitted).")
    p.add_argument("--root", choices=list(_ROOTS), required=True)
    p.add_argument("path")
    p.add_argument("--content", default=None)
    p.set_defaults(func=_cmd_fs_write)

    p = subparsers.add_parser("upload", help="Upload a local file into the shared data directory.")
    p.add_argument("--root", choices=list(_ROOTS), required=True)
    p.add_argument("path", help="Destination path relative to --root.")
    p.add_argument("local_file", help="Path to the local file to upload.")
    p.set_defaults(func=_cmd_fs_upload)

    p = subparsers.add_parser("mkdir", help="Create a directory.")
    p.add_argument("--root", choices=list(_ROOTS), required=True)
    p.add_argument("path")
    p.set_defaults(func=_cmd_fs_mkdir)

    p = subparsers.add_parser("mv", help="Move/rename a file or directory.")
    p.add_argument("--root", choices=list(_ROOTS), required=True)
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=_cmd_fs_mv)

    p = subparsers.add_parser("rm", help="Delete a file or directory.")
    p.add_argument("--root", choices=list(_ROOTS), required=True)
    p.add_argument("path")
    p.add_argument("--recursive", action="store_true", help="Delete non-empty directories recursively.")
    p.set_defaults(func=_cmd_fs_rm)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

