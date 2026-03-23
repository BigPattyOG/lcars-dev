"""Static LCARS command catalogue."""

from lcars.core.models import HelpSection

HELP_SECTIONS: tuple[HelpSection, ...] = (
    HelpSection(
        title="Core Commands",
        commands=(
            ("lcars", "Render the LCARS operations dashboard."),
            ("lcars help", "Display the command directory."),
            ("lcars version", "Display release metadata and stardate."),
            ("lcars install", "Initialize runtime configuration."),
        ),
    ),
    HelpSection(
        title="System Commands",
        commands=(
            ("lcars status", "Show current system and service state."),
            ("lcars monitor", "Live monitor CPU, memory, disk, and bot status."),
            ("lcars restart", "Restart the Discord bot service."),
            ("lcars shutdown", "Stop the Discord bot service."),
            ("lcars update", "Pull code, install dependencies, and restart."),
        ),
    ),
    HelpSection(
        title="Diagnostics",
        commands=(
            ("lcars logs", "Display recent runtime logs."),
            ("lcars doctor", "Run configuration and dependency checks."),
        ),
    ),
)


def dashboard_commands(limit: int = 6) -> list[tuple[str, str]]:
    commands: list[tuple[str, str]] = []
    for section in HELP_SECTIONS:
        commands.extend(section.commands)
    return commands[:limit]
