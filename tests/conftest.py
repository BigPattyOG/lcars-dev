from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture()
def runtime_env(tmp_path, monkeypatch):
    install_root = tmp_path / "opt" / "lcars"
    runtime_root = tmp_path / "runtime"
    state_dir = tmp_path / "state"
    logs_dir = tmp_path / "logs"
    env_path = install_root / ".env"

    monkeypatch.setenv("LCARS_INSTALL_ROOT", str(install_root))
    monkeypatch.setenv("LCARS_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("LCARS_STATE_DIR", str(state_dir))
    monkeypatch.setenv("LCARS_LOG_DIR", str(logs_dir))
    monkeypatch.setenv("LCARS_ENV_PATH", str(env_path))
    monkeypatch.setenv("NO_COLOR", "1")
    return {
        "install_root": install_root,
        "runtime_root": runtime_root,
        "state_dir": state_dir,
        "logs_dir": logs_dir,
        "env_path": env_path,
    }
