"""Shared LCARS data models."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class ReleaseVersion:
    version: str
    stardate: str
    released_at: str


@dataclass(slots=True)
class BotProcessState:
    name: str
    running: bool
    label: str
    detail: str
    pid: int | None = None
    started_at: datetime | None = None


@dataclass(slots=True)
class SystemSnapshot:
    release: ReleaseVersion
    system_status: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    uptime: str
    services: Sequence[BotProcessState]
    environment: str
    generated_at: datetime


@dataclass(slots=True)
class DiagnosticCheck:
    name: str
    status: str
    detail: str


@dataclass(slots=True)
class HelpSection:
    title: str
    commands: Sequence[tuple[str, str]]


@dataclass(slots=True)
class InstallProfile:
    discord_token: str
    environment: str


@dataclass(slots=True)
class RuntimeConfig:
    environment: str
    env_path: Path
    discord_token: str | None = None
    token_configured_flag: bool | None = None
    raw: Mapping[str, str] = field(default_factory=dict)

    @property
    def token_configured(self) -> bool:
        if self.token_configured_flag is not None:
            return self.token_configured_flag
        return bool(self.discord_token)

    def safe_pairs(self) -> list[tuple[str, str]]:
        return [
            ("Environment", self.environment),
            ("Discord Token", "CONFIGURED" if self.token_configured else "MISSING"),
            ("Env File", str(self.env_path)),
        ]
