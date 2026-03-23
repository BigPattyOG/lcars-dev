"""Installer workflow helpers."""

from __future__ import annotations

from lcars.core.config import (
    build_install_payload,
    build_public_install_payload,
    load_runtime_config,
    public_env_path,
    write_env_file,
)
from lcars.core.models import InstallProfile, RuntimeConfig
from lcars.core.paths import LcarsPaths
from lcars.systems.service import BotServiceManager


class Installer:
    """Persist LCARS runtime configuration."""

    def __init__(self, paths: LcarsPaths | None = None) -> None:
        self.paths = paths or LcarsPaths.discover()
        self.service_manager = BotServiceManager(self.paths)

    def install(self, profile: InstallProfile) -> RuntimeConfig:
        self.paths.ensure_runtime_dirs()
        write_env_file(self.paths.env_path, build_install_payload(profile))
        write_env_file(
            public_env_path(self.paths),
            build_public_install_payload(profile),
        )
        self.service_manager.write_event(
            f"Installer completed for environment {profile.environment.upper()}."
        )
        return load_runtime_config(self.paths)
