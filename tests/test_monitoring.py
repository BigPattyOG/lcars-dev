from __future__ import annotations

from types import SimpleNamespace

import psutil

from lcars.core.models import BotProcessState
from lcars.core.paths import LcarsPaths
from lcars.systems.monitoring import MonitoringService


class FakeServiceManager:
    def status(self) -> BotProcessState:
        return BotProcessState(
            name="Discord Bot",
            running=True,
            label="ONLINE",
            detail="PID 999",
            pid=999,
        )


def test_monitoring_snapshot_collects_metrics(runtime_env, monkeypatch) -> None:
    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=0.0: 21.5)
    monkeypatch.setattr(
        psutil,
        "virtual_memory",
        lambda: SimpleNamespace(percent=44.0),
    )
    monkeypatch.setattr(
        psutil,
        "disk_usage",
        lambda path: SimpleNamespace(percent=62.0),
    )
    monkeypatch.setattr(psutil, "boot_time", lambda: 100.0)
    monkeypatch.setattr("time.time", lambda: 4600.0)

    monitoring = MonitoringService(
        paths=LcarsPaths.discover(),
        service_manager=FakeServiceManager(),
    )
    snapshot = monitoring.collect_snapshot(sample_interval=0.0)

    assert snapshot.system_status == "OPERATIONAL"
    assert snapshot.cpu_percent == 21.5
    assert snapshot.memory_percent == 44.0
    assert snapshot.disk_percent == 62.0
    assert snapshot.environment == "UNCONFIGURED"
