"""LCARS Click entrypoint."""

from __future__ import annotations

import time

import click
from rich.console import Console
from rich.live import Live

from lcars.cli.ui.loading import run_spinner, run_step_progress
from lcars.cli.ui.render import (
    render_dashboard,
    render_doctor_panel,
    render_help_panel,
    render_logs_panel,
    render_message_panel,
    render_motd_panel,
    render_status_panel,
    render_version_panel,
)
from lcars.core.config import load_runtime_config
from lcars.core.models import InstallProfile
from lcars.core.paths import LcarsPaths
from lcars.core.versioning import load_release_version
from lcars.systems.doctor import run_diagnostics
from lcars.systems.installer import Installer
from lcars.systems.monitoring import MonitoringService
from lcars.systems.service import BotServiceManager
from lcars.systems.updater import UpdateManager
from lcars.utils.files import tail_lines


def _console() -> Console:
    return Console()


def _monitoring_service(paths: LcarsPaths) -> MonitoringService:
    service_manager = BotServiceManager(paths)
    return MonitoringService(paths=paths, service_manager=service_manager)


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["--help"]},
)
@click.pass_context
def main(ctx: click.Context) -> None:
    """LCARS command interface."""

    if ctx.invoked_subcommand is not None:
        return

    console = _console()
    paths = LcarsPaths.discover()
    snapshot = run_spinner(
        console,
        "Initializing LCARS systems",
        lambda: _monitoring_service(paths).collect_snapshot(),
    )
    console.print(render_dashboard(snapshot))


@main.command()
def help() -> None:
    """Display the LCARS command directory."""

    _console().print(render_help_panel())


@main.command()
def motd() -> None:
    """Display the LCARS message of the day."""

    paths = LcarsPaths.discover()
    snapshot = _monitoring_service(paths).collect_snapshot(sample_interval=0.0)
    _console().print(render_motd_panel(snapshot))


@main.command()
def status() -> None:
    """Display current LCARS system status."""

    console = _console()
    paths = LcarsPaths.discover()
    snapshot = _monitoring_service(paths).collect_snapshot(sample_interval=0.0)
    config = load_runtime_config(paths)
    console.print(render_status_panel(snapshot, config))


@main.command()
@click.option(
    "--refresh", default=1.0, show_default=True, type=click.FloatRange(0.5, 5.0)
)
def monitor(refresh: float) -> None:
    """Continuously display live LCARS metrics."""

    console = _console()
    paths = LcarsPaths.discover()
    monitoring = _monitoring_service(paths)
    try:
        with Live(
            render_dashboard(monitoring.collect_snapshot(sample_interval=0.0)),
            console=console,
            screen=True,
            auto_refresh=False,
        ) as live:
            while True:
                live.update(
                    render_dashboard(monitoring.collect_snapshot(sample_interval=0.0))
                )
                live.refresh()
                time.sleep(refresh)
    except KeyboardInterrupt:
        console.print(
            render_message_panel(
                "Monitor Halted",
                "LCARS monitoring stream halted.",
            )
        )


@main.command()
def restart() -> None:
    """Restart the LCARS Discord bot service."""

    console = _console()
    service_manager = BotServiceManager()
    try:
        state = run_spinner(
            console,
            "Routing restart through service control",
            service_manager.restart,
        )
    except RuntimeError as exc:
        console.print(render_message_panel("Restart Fault", str(exc), success=False))
        raise SystemExit(1) from exc
    console.print(
        render_message_panel(
            "Restart Complete",
            f"{state.name} {state.label}. {state.detail}",
        )
    )


@main.command()
def shutdown() -> None:
    """Stop the LCARS Discord bot service."""

    console = _console()
    service_manager = BotServiceManager()
    state = run_spinner(
        console,
        "Routing shutdown through service control",
        service_manager.stop,
    )
    console.print(
        render_message_panel(
            "Shutdown Complete",
            f"{state.name} {state.label}. {state.detail}",
        )
    )


@main.command()
def update() -> None:
    """Update the LCARS repository and restart the service."""

    console = _console()
    updater = UpdateManager()
    try:
        run_spinner(console, "Synchronizing LCARS repository", updater.git_pull)
        run_step_progress(
            console,
            "Applying LCARS update",
            (
                ("Installing dependencies", updater.install_dependencies),
                (
                    "Restarting Discord service",
                    lambda: updater.restart_service() or None,
                ),
            ),
        )
    except RuntimeError as exc:
        console.print(render_message_panel("Update Fault", str(exc), success=False))
        raise SystemExit(1) from exc

    console.print(
        render_message_panel(
            "Update Complete",
            "Command accepted. System updated.",
        )
    )


@main.command()
def version() -> None:
    """Display LCARS version metadata."""

    _console().print(render_version_panel(load_release_version()))


@main.command()
@click.option("--lines", default=40, show_default=True, type=click.IntRange(5, 500))
def logs(lines: int) -> None:
    """Display recent LCARS log output."""

    paths = LcarsPaths.discover()
    combined = ["== SYSTEM ==", *tail_lines(paths.system_log_path, lines)]
    combined.extend(["", "== BOT ==", *tail_lines(paths.bot_log_path, lines)])
    _console().print(render_logs_panel(combined))


@main.command()
def doctor() -> None:
    """Run LCARS diagnostic checks."""

    _console().print(render_doctor_panel(run_diagnostics()))


@main.command()
@click.option("--env-path", type=click.Path(path_type=str), default=None, hidden=True)
def install(env_path: str | None) -> None:
    """Initialize LCARS runtime configuration."""

    console = _console()
    console.print(
        render_message_panel(
            "Initialization", "LCARS system initialization.", success=True
        )
    )
    token = click.prompt("Discord bot token", hide_input=True)
    environment = click.prompt("Environment", default="production", show_default=True)

    paths = LcarsPaths.discover()
    if env_path:
        paths = LcarsPaths(
            repo_root=paths.repo_root,
            install_root=paths.install_root,
            runtime_root=paths.runtime_root,
            env_path=paths.env_path.__class__(env_path),
            state_dir=paths.state_dir,
            logs_dir=paths.logs_dir,
            bot_state_path=paths.bot_state_path,
            bot_log_path=paths.bot_log_path,
            system_log_path=paths.system_log_path,
        )

    installer = Installer(paths)
    profile = InstallProfile(discord_token=token, environment=environment)

    try:
        run_spinner(
            console,
            "Initializing LCARS runtime",
            paths.ensure_runtime_dirs,
        )
        run_step_progress(
            console,
            "Applying installation profile",
            (
                ("Persisting environment profile", lambda: installer.install(profile)),
                (
                    "Registering system operational state",
                    lambda: installer.service_manager.write_event(
                        "LCARS initialization complete. System operational."
                    ),
                ),
            ),
        )
    except OSError as exc:
        console.print(
            render_message_panel("Initialization Fault", str(exc), success=False)
        )
        raise SystemExit(1) from exc

    console.print(
        render_message_panel(
            "Initialization Complete",
            "LCARS initialization complete. System operational.",
        )
    )
