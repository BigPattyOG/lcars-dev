"""System monitoring and snapshot generation."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import psutil

from lcars.core.config import load_runtime_config
from lcars.core.models import SystemSnapshot
from lcars.core.paths import LcarsPaths
from lcars.core.versioning import load_release_version
from lcars.systems.service import BotServiceManager
from lcars.utils.time import format_duration


class MonitoringService:
    """Collect LCARS dashboard metrics."""

    def __init__(
        self,
        paths: LcarsPaths | None = None,
        service_manager: BotServiceManager | None = None,
    ) -> None:
        self.paths = paths or LcarsPaths.discover()
        self.service_manager = service_manager or BotServiceManager(self.paths)

    def collect_snapshot(self, sample_interval: float = 0.1) -> SystemSnapshot:
        release = load_release_version()
        config = load_runtime_config(self.paths)
        bot_state = self.service_manager.status()
        cpu_percent = psutil.cpu_percent(interval=sample_interval)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage("/").percent
        uptime = format_duration(time.time() - psutil.boot_time())

        if bot_state.running:
            system_status = "OPERATIONAL"
        elif config.token_configured:
            system_status = "STANDBY"
        else:
            system_status = "CONFIG REQUIRED"

        return SystemSnapshot(
            release=release,
            system_status=system_status,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            uptime=uptime,
            services=[bot_state],
            environment=config.environment,
            generated_at=datetime.now(UTC),
        )
