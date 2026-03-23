"""Discord bot process supervision."""

from __future__ import annotations

import os
import shutil
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
        if self._uses_systemd():
            return self._systemd_status()
        return self._subprocess_status()

    def _subprocess_status(self) -> BotProcessState:
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

    def _systemd_status(self) -> BotProcessState:
        load_state = self._systemctl_value("LoadState", check=False) or "not-found"
        if load_state == "not-found":
            return BotProcessState(
                name="Discord Bot",
                running=False,
                label="OFFLINE",
                detail=f"systemd unit {self.paths.service_name} not installed.",
            )

        active_state = self._systemctl_value("ActiveState", check=False) or "inactive"
        sub_state = self._systemctl_value("SubState", check=False) or "dead"
        pid = int((self._systemctl_value("MainPID", check=False) or "0").strip() or 0)
        started_at = self._started_at_from_state(pid)

        if active_state == "active":
            detail_parts = [f"systemd {active_state}/{sub_state}"]
            if pid > 0:
                detail_parts.append(f"PID {pid}")
            if started_at is not None:
                detail_parts.append(f"Since {format_timestamp(started_at)}")
            return BotProcessState(
                name="Discord Bot",
                running=True,
                label="ONLINE",
                detail=" | ".join(detail_parts),
                pid=pid if pid > 0 else None,
                started_at=started_at,
            )

        self.clear_state()
        return BotProcessState(
            name="Discord Bot",
            running=False,
            label="OFFLINE",
            detail=f"systemd {active_state}/{sub_state}",
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
        if self._uses_systemd():
            self.paths.ensure_runtime_dirs()
            self._run_systemctl("start", self.paths.service_name)
            time.sleep(0.6)
            state = self.status()
            if not state.running:
                raise RuntimeError(f"Bot startup failed. {state.detail}")
            self.write_event("Discord bot started via systemd.")
            return state

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
        if self._uses_systemd():
            self._run_systemctl("stop", self.paths.service_name)
            time.sleep(0.3)
            state = self.status()
            self.write_event("Discord bot stopped via systemd.")
            return state

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
        if self._uses_systemd():
            self.paths.ensure_runtime_dirs()
            self._run_systemctl("restart", self.paths.service_name)
            time.sleep(0.6)
            state = self.status()
            if not state.running:
                raise RuntimeError(f"Bot restart failed. {state.detail}")
            self.write_event("Discord bot restarted via systemd.")
            return state

        self.stop()
        return self.start()

    def _uses_systemd(self) -> bool:
        if shutil.which("systemctl") is None:
            return False
        return (
            os.environ.get("LCARS_SYSTEMD_MANAGED") == "1"
            or self.paths.systemd_marker_path.exists()
        )

    def _run_systemctl(self, action: str, service_name: str) -> str:
        completed = subprocess.run(  # noqa: S603
            ["systemctl", action, service_name],
            check=False,
            capture_output=True,
            text=True,
        )
        output = completed.stdout.strip() or completed.stderr.strip()
        if completed.returncode != 0:
            raise RuntimeError(output or f"systemctl {action} {service_name} failed.")
        return output or "Command completed."

    def _systemctl_value(self, property_name: str, *, check: bool) -> str:
        completed = subprocess.run(  # noqa: S603
            [
                "systemctl",
                "show",
                f"--property={property_name}",
                "--value",
                self.paths.service_name,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        output = completed.stdout.strip() or completed.stderr.strip()
        if check and completed.returncode != 0:
            raise RuntimeError(
                output
                or (
                    f"Unable to query {property_name} "
                    f"for {self.paths.service_name}."
                )
            )
        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()

    def _started_at_from_state(self, pid: int) -> datetime | None:
        payload = read_json(self.paths.bot_state_path) or {}
        started_at_raw = payload.get("started_at")
        if started_at_raw:
            return datetime.fromisoformat(started_at_raw)

        if pid <= 0:
            return None

        try:
            process = psutil.Process(pid)
        except psutil.Error:
            return None
        return datetime.fromtimestamp(process.create_time(), tz=UTC)
