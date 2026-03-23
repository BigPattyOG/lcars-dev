"""Discord bot runtime entrypoint."""

from __future__ import annotations

import os

from lcars.core.config import load_runtime_config
from lcars.core.paths import LcarsPaths
from lcars.modules.discord.bot import LcarsBot
from lcars.systems.service import BotServiceManager


def main() -> None:
    paths = LcarsPaths.discover()
    service_manager = BotServiceManager(paths)
    service_manager.record_current_process(os.getpid())
    config = load_runtime_config(paths)
    if not config.token_configured:
        service_manager.write_event("Discord bot startup aborted. Token missing.")
        raise SystemExit("LCARS Discord token not configured.")

    service_manager.write_event("Discord bot runtime starting.")
    bot = LcarsBot(paths=paths, service_manager=service_manager)
    try:
        bot.run(config.discord_token, log_handler=None)
    finally:
        service_manager.clear_state()
        service_manager.write_event("Discord bot runtime stopped.")


if __name__ == "__main__":
    main()
