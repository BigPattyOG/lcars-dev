from __future__ import annotations

from click.testing import CliRunner

from lcars.cli.main import main


def test_help_command_renders_sections(runtime_env) -> None:
    result = CliRunner().invoke(main, ["help"])

    assert result.exit_code == 0
    assert "Core Commands" in result.output
    assert "System Commands" in result.output
    assert "Diagnostics" in result.output


def test_version_command_renders_stardate(runtime_env) -> None:
    result = CliRunner().invoke(main, ["version"])

    assert result.exit_code == 0
    assert "2026.082.1" in result.output


def test_dashboard_renders_motd(runtime_env) -> None:
    result = CliRunner().invoke(main, [])

    assert result.exit_code == 0
    assert "LCARS COMPUTER INTERFACE" in result.output
    assert "Command Directory" in result.output


def test_motd_command_renders_message(runtime_env) -> None:
    result = CliRunner().invoke(main, ["motd"])

    assert result.exit_code == 0
    assert "LCARS COMPUTER INTERFACE" in result.output
    assert "LCARS MOTD" in result.output
