"""System diagnostics."""

from __future__ import annotations

import importlib
import os

from lcars.core.config import load_runtime_config
from lcars.core.models import DiagnosticCheck
from lcars.core.paths import LcarsPaths
from lcars.systems.service import BotServiceManager


def run_diagnostics(
    paths: LcarsPaths | None = None,
    service_manager: BotServiceManager | None = None,
) -> list[DiagnosticCheck]:
    resolved_paths = paths or LcarsPaths.discover()
    resolved_service = service_manager or BotServiceManager(resolved_paths)
    config = load_runtime_config(resolved_paths)
    bot_state = resolved_service.status()

    checks = [
        DiagnosticCheck(
            name="Environment File",
            status="OK" if resolved_paths.env_path.exists() else "WARN",
            detail=str(resolved_paths.env_path),
        ),
        DiagnosticCheck(
            name="Discord Token",
            status="OK" if config.token_configured else "FAIL",
            detail="Configured" if config.token_configured else "Token missing.",
        ),
        DiagnosticCheck(
            name="Git Repository",
            status="OK" if (resolved_paths.repo_root / ".git").exists() else "WARN",
            detail=str(resolved_paths.repo_root),
        ),
        DiagnosticCheck(
            name="Runtime Root",
            status=(
                "OK"
                if os.access(resolved_paths.runtime_root.parent, os.W_OK)
                or resolved_paths.runtime_root.exists()
                else "WARN"
            ),
            detail=str(resolved_paths.runtime_root),
        ),
        DiagnosticCheck(
            name="Discord Bot",
            status="OK" if bot_state.running else "WARN",
            detail=bot_state.detail,
        ),
    ]

    for module_name in ("click", "rich", "psutil", "discord"):
        try:
            importlib.import_module(module_name)
        except ImportError:
            checks.append(
                DiagnosticCheck(
                    name=f"Dependency:{module_name}",
                    status="FAIL",
                    detail="Package import failed.",
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    name=f"Dependency:{module_name}",
                    status="OK",
                    detail="Package import succeeded.",
                )
            )

    return checks
