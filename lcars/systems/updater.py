"""Repository update workflow helpers."""

from __future__ import annotations

import subprocess
import sys

from lcars.core.paths import LcarsPaths
from lcars.systems.service import BotServiceManager


class UpdateManager:
    """Run git and dependency refresh operations."""

    def __init__(
        self,
        paths: LcarsPaths | None = None,
        service_manager: BotServiceManager | None = None,
    ) -> None:
        self.paths = paths or LcarsPaths.discover()
        self.service_manager = service_manager or BotServiceManager(self.paths)

    def git_pull(self) -> str:
        return self._run_command(["git", "pull", "--ff-only"])

    def install_dependencies(self) -> str:
        return self._run_command([sys.executable, "-m", "pip", "install", "-e", "."])

    def restart_service(self) -> None:
        self.service_manager.restart()
        self.service_manager.write_event("Update workflow restarted Discord bot.")

    def _run_command(self, command: list[str]) -> str:
        completed = subprocess.run(  # noqa: S603
            command,
            cwd=self.paths.repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        output = completed.stdout.strip() or completed.stderr.strip()
        if completed.returncode != 0:
            raise RuntimeError(output or f"Command failed: {' '.join(command)}")
        return output or "Command completed."
