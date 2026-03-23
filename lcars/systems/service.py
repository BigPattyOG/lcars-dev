"""Discord bot process supervision."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import UTC, datetime

import psutil

from lcars.core.models import BotProcessState
from lcars.core.paths import LcarsPaths
from lcars.utils.files import read_json, tail_lines, write_json_atomic
from lcars.utils.time import format_timestamp, utc_now


class BotServiceManager:
    """Manage the LCARS Discord bot subprocess."""

    def __init__(self, paths: LcarsPaths | None = None) -> None:
        self.paths = paths or LcarsPaths.discover()

    def status(self) -> BotProcessState:
        payload = read_json(self.paths.bot_state_path)
        if not payload:
            return BotProcessState(
                name="Discord Bot",
                running=False,
                label="OFFLINE",
                detail="No active process record.",
            )

        pid = int(payload.get("pid", 0))
        if pid <= 0:
            self.clear_state()
            return BotProcessState(
                name="Discord Bot",
                running=False,
                label="OFFLINE",
                detail="Invalid process record removed.",
            )

        try:
            process = psutil.Process(pid)
            if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                raise psutil.Error()
        except psutil.Error:
            self.clear_state()
            return BotProcessState(
                name="Discord Bot",
                running=False,
                label="OFFLINE",
                detail="Stale process record cleared.",
            )

        started_at_raw = payload.get("started_at")
        started_at = (
            datetime.fromisoformat(started_at_raw)
            if started_at_raw
            else datetime.fromtimestamp(process.create_time(), tz=UTC)
        )
        return BotProcessState(
            name="Discord Bot",
            running=True,
            label="ONLINE",
            detail=f"PID {pid} | Since {format_timestamp(started_at)}",
            pid=pid,
            started_at=started_at,
        )

    def record_current_process(self, pid: int | None = None) -> None:
        self.paths.ensure_runtime_dirs()
        active_pid = pid or os.getpid()
        write_json_atomic(
            self.paths.bot_state_path,
            {
                "pid": active_pid,
                "started_at": utc_now().isoformat(),
            },
        )

    def clear_state(self) -> None:
        if self.paths.bot_state_path.exists():
            self.paths.bot_state_path.unlink()

    def write_event(self, message: str) -> None:
        self.paths.ensure_runtime_dirs()
        line = f"{utc_now().isoformat()} | {message}\n"
        with self.paths.system_log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def start(self) -> BotProcessState:
        current = self.status()
        if current.running:
            return current

        self.paths.ensure_runtime_dirs()
        command = [sys.executable, "-m", "lcars.systems.bot_runtime"]
        with self.paths.bot_log_path.open("a", encoding="utf-8") as log_handle:
            process = subprocess.Popen(  # noqa: S603
                command,
                cwd=self.paths.repo_root,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=os.environ.copy(),
            )

        time.sleep(0.6)
        if process.poll() is not None:
            self.clear_state()
            excerpt = " ".join(tail_lines(self.paths.bot_log_path, 5))
            raise RuntimeError(f"Bot startup failed. {excerpt}")

        self.record_current_process(process.pid)
        self.write_event("Discord bot started.")
        return self.status()

    def stop(self, timeout: float = 10.0) -> BotProcessState:
        current = self.status()
        if not current.running or current.pid is None:
            self.clear_state()
            return BotProcessState(
                name="Discord Bot",
                running=False,
                label="OFFLINE",
                detail="No active process to stop.",
            )

        try:
            process = psutil.Process(current.pid)
            process.terminate()
            process.wait(timeout=timeout)
        except psutil.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        except psutil.Error:
            pass

        self.clear_state()
        self.write_event("Discord bot stopped.")
        return BotProcessState(
            name="Discord Bot",
            running=False,
            label="OFFLINE",
            detail="Service stopped.",
        )

    def restart(self) -> BotProcessState:
        self.stop()
        return self.start()
