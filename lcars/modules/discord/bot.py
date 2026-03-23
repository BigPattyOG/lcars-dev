"""Discord bot implementation for LCARS."""

import asyncio
import os
import sys

import discord
from discord.ext import commands

from lcars.core.catalog import HELP_SECTIONS
from lcars.core.paths import LcarsPaths
from lcars.core.versioning import load_release_version
from lcars.systems.monitoring import MonitoringService
from lcars.systems.service import BotServiceManager

LCARS_ORANGE = 0xF6A04D
LCARS_CYAN = 0x78DDF0
LCARS_GREEN = 0x71D99E
LCARS_RED = 0xF07178


class LcarsBot(commands.Bot):
    """LCARS slash-command bot."""

    def __init__(
        self,
        *,
        paths: LcarsPaths | None = None,
        service_manager: BotServiceManager | None = None,
    ) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(command_prefix="lcars:", intents=intents)
        self.paths = paths or LcarsPaths.discover()
        self.service_manager = service_manager or BotServiceManager(self.paths)
        self.monitoring = MonitoringService(
            paths=self.paths,
            service_manager=self.service_manager,
        )
        self.release = load_release_version()
        self._commands_registered = False

    async def setup_hook(self) -> None:
        if not self._commands_registered:
            self._register_commands()
            self._commands_registered = True
        await self.tree.sync()

    async def on_ready(self) -> None:
        identity = self.user.name if self.user else "unknown"
        self.service_manager.write_event(f"Discord bot connected as {identity}.")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        channel = self._welcome_channel(guild)
        if channel is None:
            return
        embed = discord.Embed(
            title="LCARS SYSTEM INITIALIZED",
            description=(
                "System connection established.\n\n"
                "Use /help to access command directory.\n\n"
                "Live long and prosper. 🖖"
            ),
            color=LCARS_ORANGE,
        )
        embed.set_footer(text=f"Stardate {self.release.stardate}")
        await channel.send(embed=embed)

    def _register_commands(self) -> None:
        @self.tree.command(
            name="help", description="Display the LCARS command directory."
        )
        async def help_command(interaction: discord.Interaction) -> None:
            embed = self._base_embed(
                title="LCARS COMMAND DIRECTORY",
                description="Structured command index.",
                color=LCARS_ORANGE,
            )
            for section in HELP_SECTIONS:
                value = "\n".join(
                    f"`{command}`\n{description}"
                    for command, description in section.commands
                )
                embed.add_field(name=section.title, value=value, inline=False)
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="version", description="Display release metadata.")
        async def version_command(interaction: discord.Interaction) -> None:
            embed = self._base_embed(
                title="LCARS VERSION DIRECTORY",
                description="Static release metadata.",
                color=LCARS_CYAN,
            )
            embed.add_field(name="Version", value=self.release.version, inline=True)
            embed.add_field(name="Stardate", value=self.release.stardate, inline=True)
            embed.add_field(
                name="Released",
                value=self.release.released_at,
                inline=False,
            )
            await interaction.response.send_message(embed=embed)

        @self.tree.command(
            name="status", description="Display the LCARS system status."
        )
        async def status_command(interaction: discord.Interaction) -> None:
            snapshot = self.monitoring.collect_snapshot(sample_interval=0.0)
            service = snapshot.services[0]
            embed = self._base_embed(
                title="LCARS SYSTEM STATUS",
                description=f"System status: {snapshot.system_status}",
                color=(
                    LCARS_GREEN
                    if snapshot.system_status == "OPERATIONAL"
                    else LCARS_ORANGE
                ),
            )
            embed.add_field(
                name="CPU", value=f"{snapshot.cpu_percent:.1f}%", inline=True
            )
            embed.add_field(
                name="Memory",
                value=f"{snapshot.memory_percent:.1f}%",
                inline=True,
            )
            embed.add_field(
                name="Disk", value=f"{snapshot.disk_percent:.1f}%", inline=True
            )
            embed.add_field(name="Uptime", value=snapshot.uptime, inline=True)
            embed.add_field(name="Service", value=service.label, inline=True)
            embed.add_field(name="Detail", value=service.detail, inline=False)
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="restart", description="Restart the LCARS bot runtime.")
        async def restart_command(interaction: discord.Interaction) -> None:
            if not self._can_control_system(interaction):
                await interaction.response.send_message(
                    embed=self._base_embed(
                        title="ACCESS DENIED",
                        description="System control requires administrator privileges.",
                        color=LCARS_RED,
                    ),
                    ephemeral=True,
                )
                return

            await interaction.response.send_message(
                embed=self._base_embed(
                    title="RESTART ACCEPTED",
                    description="Restart sequence initiated.",
                    color=LCARS_ORANGE,
                ),
                ephemeral=True,
            )
            asyncio.create_task(self._restart_process())

        @self.tree.command(name="shutdown", description="Stop the LCARS bot runtime.")
        async def shutdown_command(interaction: discord.Interaction) -> None:
            if not self._can_control_system(interaction):
                await interaction.response.send_message(
                    embed=self._base_embed(
                        title="ACCESS DENIED",
                        description="System control requires administrator privileges.",
                        color=LCARS_RED,
                    ),
                    ephemeral=True,
                )
                return

            await interaction.response.send_message(
                embed=self._base_embed(
                    title="SHUTDOWN ACCEPTED",
                    description="Shutdown sequence initiated.",
                    color=LCARS_ORANGE,
                ),
                ephemeral=True,
            )
            asyncio.create_task(self._shutdown_process())

    def _base_embed(self, *, title: str, description: str, color: int) -> discord.Embed:
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=f"Stardate {self.release.stardate}")
        return embed

    def _can_control_system(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False
        permissions = interaction.user.guild_permissions
        return bool(permissions.administrator or permissions.manage_guild)

    def _welcome_channel(self, guild: discord.Guild) -> discord.abc.Messageable | None:
        me = guild.me
        if guild.system_channel and me is not None:
            permissions = guild.system_channel.permissions_for(me)
            if permissions.send_messages and permissions.embed_links:
                return guild.system_channel
        for channel in guild.text_channels:
            if me is None:
                return channel
            permissions = channel.permissions_for(me)
            if permissions.send_messages and permissions.embed_links:
                return channel
        return None

    async def _restart_process(self) -> None:
        await asyncio.sleep(1)
        self.service_manager.write_event("Discord slash command requested restart.")
        os.execv(sys.executable, [sys.executable, "-m", "lcars.systems.bot_runtime"])

    async def _shutdown_process(self) -> None:
        await asyncio.sleep(1)
        self.service_manager.write_event("Discord slash command requested shutdown.")
        self.service_manager.clear_state()
        await self.close()
