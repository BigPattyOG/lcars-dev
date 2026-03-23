"""Filesystem path resolution for LCARS."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LcarsPaths:
    repo_root: Path
    install_root: Path
    runtime_root: Path
    env_path: Path
    state_dir: Path
    logs_dir: Path
    bot_state_path: Path
    bot_log_path: Path
    system_log_path: Path

    @classmethod
    def discover(cls) -> LcarsPaths:
        install_root = Path(
            os.environ.get("LCARS_INSTALL_ROOT", "/opt/lcars")
        ).expanduser()
        repo_root_env = os.environ.get("LCARS_REPO_ROOT")
        if repo_root_env:
            repo_root = Path(repo_root_env).expanduser()
        else:
            package_path = Path(__file__).resolve()
            repo_root = next(
                (
                    parent
                    for parent in package_path.parents
                    if (parent / ".git").exists()
                ),
                install_root / "app",
            )
        runtime_root = Path(
            os.environ.get("LCARS_RUNTIME_ROOT", str(install_root))
        ).expanduser()
        env_path = Path(
            os.environ.get("LCARS_ENV_PATH", str(install_root / ".env"))
        ).expanduser()
        state_dir = Path(
            os.environ.get("LCARS_STATE_DIR", str(runtime_root / "state"))
        ).expanduser()
        logs_dir = Path(
            os.environ.get("LCARS_LOG_DIR", str(runtime_root / "logs"))
        ).expanduser()
        return cls(
            repo_root=repo_root,
            install_root=install_root,
            runtime_root=runtime_root,
            env_path=env_path,
            state_dir=state_dir,
            logs_dir=logs_dir,
            bot_state_path=state_dir / "bot.json",
            bot_log_path=logs_dir / "bot.log",
            system_log_path=logs_dir / "system.log",
        )

    def ensure_runtime_dirs(self) -> None:
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def service_name(self) -> str:
        return os.environ.get("LCARS_SERVICE_NAME", "lcars.service")

    @property
    def systemd_marker_path(self) -> Path:
        return self.install_root / "systemd-managed"
