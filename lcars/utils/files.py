"""Filesystem helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    write_text_atomic(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def tail_lines(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return ["Log file not found."]
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:] or ["Log file is empty."]
