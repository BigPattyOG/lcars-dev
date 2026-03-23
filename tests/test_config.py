from __future__ import annotations

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
