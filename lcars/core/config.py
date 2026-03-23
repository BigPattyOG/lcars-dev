"""LCARS runtime configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path

from lcars.core.models import InstallProfile, RuntimeConfig
from lcars.core.paths import LcarsPaths
from lcars.utils.files import write_text_atomic


def parse_env(raw_text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return parse_env(path.read_text(encoding="utf-8"))


def build_install_payload(profile: InstallProfile) -> dict[str, str]:
    return {
        "LCARS_ENVIRONMENT": profile.environment.upper(),
        "LCARS_DISCORD_TOKEN": profile.discord_token,
        "LCARS_LOG_LEVEL": "INFO",
    }


def write_env_file(path: Path, payload: dict[str, str]) -> None:
    lines = ["# LCARS runtime configuration"]
    for key in sorted(payload):
        lines.append(f"{key}={payload[key]}")
    write_text_atomic(path, "\n".join(lines) + "\n")


def load_runtime_config(paths: LcarsPaths | None = None) -> RuntimeConfig:
    resolved_paths = paths or LcarsPaths.discover()
    payload = load_env_file(resolved_paths.env_path)
    for key, value in os.environ.items():
        if key.startswith("LCARS_"):
            payload[key] = value
    return RuntimeConfig(
        environment=payload.get("LCARS_ENVIRONMENT", "UNCONFIGURED"),
        env_path=resolved_paths.env_path,
        discord_token=payload.get("LCARS_DISCORD_TOKEN"),
        raw=payload,
    )
