"""Rich renderables for LCARS output."""

from __future__ import annotations

from rich.align import Align
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lcars.cli.ui import theme
from lcars.core.catalog import HELP_SECTIONS, dashboard_commands
from lcars.core.config import RuntimeConfig
from lcars.core.models import DiagnosticCheck, ReleaseVersion, SystemSnapshot
from lcars.core.versioning import build_motd
from lcars.utils.time import format_timestamp


def _panel(renderable, title: str) -> Panel:
    return Panel(
        renderable,
        title=f"[{theme.HEADER_PURPLE}]{title}[/]",
        border_style=theme.PANEL_ORANGE,
        padding=(1, 2),
    )


def _metric_table(snapshot: SystemSnapshot) -> Table:
    table = Table.grid(expand=True, padding=(0, 2))
    table.add_column(style=theme.HEADER_PURPLE)
    table.add_column(justify="right", style=theme.VALUE_CYAN)
    table.add_row("CPU", f"{snapshot.cpu_percent:.1f}%")
    table.add_row("RAM", f"{snapshot.memory_percent:.1f}%")
    table.add_row("Disk", f"{snapshot.disk_percent:.1f}%")
    table.add_row("Uptime", snapshot.uptime)
    return table


def _service_table(snapshot: SystemSnapshot) -> Table:
    table = Table.grid(expand=True, padding=(0, 2))
    table.add_column(style=theme.HEADER_PURPLE)
    table.add_column(style=theme.VALUE_CYAN)
    for service in snapshot.services:
        table.add_row(
            service.name,
            f"[{theme.status_style(service.label)}]{service.label}[/]\n"
            f"[{theme.TEXT_MUTED}]{service.detail}[/]",
        )
    table.add_row("Environment", snapshot.environment)
    table.add_row("Generated", format_timestamp(snapshot.generated_at))
    return table


def _commands_table() -> Table:
    table = Table.grid(expand=True, padding=(0, 2))
    table.add_column(style=theme.HEADER_PURPLE)
    table.add_column(style=theme.TEXT_NEUTRAL)
    for command, description in dashboard_commands():
        table.add_row(command, description)
    return table


def render_dashboard(snapshot: SystemSnapshot) -> Group:
    motd = Text(
        build_motd(snapshot.release, snapshot.system_status), style=theme.VALUE_CYAN
    )
    release_table = Table.grid(expand=True)
    release_table.padding = (0, 2)
    release_table.add_column(style=theme.HEADER_PURPLE)
    release_table.add_column(style=theme.VALUE_CYAN, justify="right")
    release_table.add_row("Version", snapshot.release.version)
    release_table.add_row("Stardate", snapshot.release.stardate)
    release_table.add_row(
        "System Status",
        f"[{theme.status_style(snapshot.system_status)}]{snapshot.system_status}[/]",
    )

    top = Columns(
        [
            _panel(Align.left(motd), "LCARS MOTD"),
            _panel(release_table, "Release Channel"),
        ],
        equal=True,
        expand=True,
    )
    middle = Columns(
        [
            _panel(_metric_table(snapshot), "System Metrics"),
            _panel(_service_table(snapshot), "Services"),
        ],
        equal=True,
        expand=True,
    )
    bottom = _panel(_commands_table(), "Command Directory")
    return Group(top, middle, bottom)


def render_motd_panel(snapshot: SystemSnapshot) -> Panel:
    motd = Text(
        build_motd(snapshot.release, snapshot.system_status), style=theme.VALUE_CYAN
    )
    return _panel(Align.left(motd), "LCARS MOTD")


def render_help_panel() -> Columns:
    sections = []
    for section in HELP_SECTIONS:
        table = Table.grid(expand=True, padding=(0, 2))
        table.add_column(style=theme.HEADER_PURPLE)
        table.add_column(style=theme.TEXT_NEUTRAL)
        for command, description in section.commands:
            table.add_row(command, description)
        sections.append(_panel(table, section.title))
    return Columns(sections, equal=True, expand=True)


def render_status_panel(snapshot: SystemSnapshot, config: RuntimeConfig) -> Group:
    config_table = Table.grid(expand=True)
    config_table.padding = (0, 2)
    config_table.add_column(style=theme.HEADER_PURPLE)
    config_table.add_column(style=theme.VALUE_CYAN)
    for key, value in config.safe_pairs():
        config_table.add_row(key, value)
    return Group(
        render_dashboard(snapshot),
        _panel(config_table, "Configuration"),
    )


def render_version_panel(release: ReleaseVersion) -> Panel:
    table = Table.grid(expand=True, padding=(0, 2))
    table.add_column(style=theme.HEADER_PURPLE)
    table.add_column(style=theme.VALUE_CYAN)
    table.add_row("Version", release.version)
    table.add_row("Stardate", release.stardate)
    table.add_row("Released", release.released_at)
    return _panel(table, "Version Directory")


def render_logs_panel(lines: list[str]) -> Panel:
    content = Text("\n".join(lines), style=theme.VALUE_CYAN)
    return _panel(Align.left(content), "Log Buffer")


def render_doctor_panel(checks: list[DiagnosticCheck]) -> Panel:
    table = Table(expand=True, show_edge=False, box=None, pad_edge=False)
    table.add_column("Check", style=theme.HEADER_PURPLE)
    table.add_column("Status", style=theme.VALUE_CYAN, width=16)
    table.add_column("Detail", style=theme.TEXT_NEUTRAL)
    for check in checks:
        table.add_row(
            check.name,
            f"[{theme.status_style(check.status)}]{check.status}[/]",
            check.detail,
        )
    return _panel(table, "Diagnostic Matrix")


def render_message_panel(title: str, body: str, *, success: bool = True) -> Panel:
    style = theme.SUCCESS_GREEN if success else theme.ERROR_RED
    return Panel(
        Text(body, style=style),
        title=f"[{theme.HEADER_PURPLE}]{title}[/]",
        border_style=theme.PANEL_ORANGE_DARK,
        padding=(1, 2),
    )
