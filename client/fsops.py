"""Sandboxed filesystem operations against a directory on the shared bind mount."""
from pathlib import Path
from typing import Any, Dict, List


def _resolve(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"path escapes root: {relative_path}")
    return target


def list_files(root: Path, relative_path: str = ".") -> List[Dict[str, Any]]:
    target = _resolve(root, relative_path)
    if not target.exists():
        raise FileNotFoundError(str(target))
    if target.is_file():
        stat = target.stat()
        return [{"name": target.name, "is_dir": False, "size": stat.st_size}]

    entries = []
    for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
        stat = entry.stat()
        entries.append({"name": entry.name, "is_dir": entry.is_dir(), "size": stat.st_size})
    return entries


def read_file(root: Path, relative_path: str) -> str:
    target = _resolve(root, relative_path)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    return target.read_text(encoding="utf-8")


def read_file_bytes(root: Path, relative_path: str) -> bytes:
    target = _resolve(root, relative_path)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    return target.read_bytes()


def write_file(root: Path, relative_path: str, content: str) -> None:
    target = _resolve(root, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def write_file_bytes(root: Path, relative_path: str, content: bytes) -> None:
    target = _resolve(root, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def make_dir(root: Path, relative_path: str) -> None:
    target = _resolve(root, relative_path)
    target.mkdir(parents=True, exist_ok=True)


def move(root: Path, src_relative_path: str, dst_relative_path: str) -> None:
    src = _resolve(root, src_relative_path)
    dst = _resolve(root, dst_relative_path)
    if not src.exists():
        raise FileNotFoundError(str(src))
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)


def delete_file(root: Path, relative_path: str, recursive: bool = False) -> bool:
    target = _resolve(root, relative_path)
    if target.is_dir():
        if recursive:
            import shutil

            shutil.rmtree(target)
        else:
            target.rmdir()
        return True
    if target.is_file():
        target.unlink()
        return True
    return False

