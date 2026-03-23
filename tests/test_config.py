from __future__ import annotations

from pathlib import Path

from lcars.core.config import build_install_payload, load_runtime_config, write_env_file
from lcars.core.models import InstallProfile
from lcars.core.paths import LcarsPaths


def test_install_profile_round_trips_to_env(runtime_env) -> None:
    paths = LcarsPaths.discover()
    profile = InstallProfile(discord_token="test-token", environment="production")

    write_env_file(paths.env_path, build_install_payload(profile))
    config = load_runtime_config(paths)

    assert config.environment == "PRODUCTION"
    assert config.discord_token == "test-token"
    assert config.token_configured is True


def test_load_runtime_config_handles_permission_denied(
    runtime_env, monkeypatch
) -> None:
    paths = LcarsPaths.discover()
    paths.env_path.parent.mkdir(parents=True, exist_ok=True)
    paths.env_path.write_text("LCARS_DISCORD_TOKEN=token\n", encoding="utf-8")

    def raise_permission_error(self: Path, encoding: str = "utf-8") -> str:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_text", raise_permission_error)

    config = load_runtime_config(paths)

    assert config.environment == "UNCONFIGURED"
    assert config.discord_token is None
