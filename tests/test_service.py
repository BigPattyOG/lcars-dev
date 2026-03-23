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
