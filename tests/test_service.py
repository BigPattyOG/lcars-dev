from __future__ import annotations

import os

from lcars.core.paths import LcarsPaths
from lcars.systems.service import BotServiceManager


def test_service_status_without_record(runtime_env) -> None:
    manager = BotServiceManager(LcarsPaths.discover())

    state = manager.status()

    assert state.running is False
    assert state.label == "OFFLINE"


def test_service_record_current_process(runtime_env) -> None:
    manager = BotServiceManager(LcarsPaths.discover())

    manager.record_current_process()
    state = manager.status()
    manager.clear_state()

    assert state.running is True
    assert state.pid == os.getpid()


def test_service_uses_systemd_when_marker_exists(runtime_env, monkeypatch) -> None:
    paths = LcarsPaths.discover()
    paths.systemd_marker_path.parent.mkdir(parents=True, exist_ok=True)
    paths.systemd_marker_path.write_text("", encoding="utf-8")
    manager = BotServiceManager(paths)
    monkeypatch.setattr("shutil.which", lambda name: None)

    assert manager._uses_systemd() is False


def test_systemd_status_uses_service_metadata(runtime_env, monkeypatch) -> None:
    paths = LcarsPaths.discover()
    paths.systemd_marker_path.parent.mkdir(parents=True, exist_ok=True)
    paths.systemd_marker_path.write_text("", encoding="utf-8")
    manager = BotServiceManager(paths)

    manager.record_current_process()
    monkeypatch.setattr("shutil.which", lambda name: "/bin/systemctl")
    responses = {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "running",
        "MainPID": str(os.getpid()),
    }
    monkeypatch.setattr(
        manager,
        "_systemctl_value",
        lambda property_name, check=False: responses[property_name],
    )

    state = manager.status()

    assert state.running is True
    assert state.label == "ONLINE"
    assert state.pid == os.getpid()
    assert "systemd active/running" in state.detail
