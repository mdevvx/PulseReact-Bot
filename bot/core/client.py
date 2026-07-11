"""
Custom Bot class. Handles intents, cog auto-loading, and global
error handlers for both prefix commands and slash commands.
"""

import traceback
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.group import pulsereact_group
from bot.core.config import config
from bot.core.logger import get_logger

logger = get_logger("core.client")

# Cogs are loaded in this order. Owner cog first so kick!sync is
# always available even if another cog fails to load.
COG_MODULES = [
    "bot.cogs.owner.sync",
    "bot.cogs.general.status",
    "bot.cogs.admin.toggle",
    "bot.cogs.autoreact.commands",
    "bot.cogs.autoreact.listener",
]


class PulseReactBot(commands.Bot):
    """
    Main bot client. Every server it joins is treated independently,
    all per-guild state (enabled/disabled, autoreact config) is looked
    up from Supabase using guild_id, so no data ever crosses servers.
    """

    def __init__(self) -> None:
        # Only request the intents we actually need.
        # message_content is required to inspect message text/attachments
        # for the auto-react message-type filtering (text/image/link/etc).
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True

        super().__init__(
            command_prefix="kick!",
            intents=intents,
            help_command=None,  # We are not using the default help command.
            owner_id=config.owner_id,  # Enables commands.is_owner() checks.
        )

        # Recorded here (not on_ready, which can fire more than once on
        # reconnects) so uptime in /pulsereact status stays accurate.
        self.start_time = datetime.now(timezone.utc)

    async def setup_hook(self) -> None:
        """
        Called once by discord.py before the bot connects to the gateway.
        This is the correct place to load cogs and register error handlers,
        rather than doing it in on_ready (which can fire multiple times).
        """
        for module in COG_MODULES:
            try:
                await self.load_extension(module)
                logger.info(f"Loaded cog: {module}")
            except Exception:
                # Log full traceback but don't crash the whole bot if one
                # cog fails, the rest should still function.
                logger.error(f"Failed to load cog: {module}\n{traceback.format_exc()}")

        # Cogs attach their subcommands to pulsereact_group at import time
        # (via decorators), so the group is only added to the tree once,
        # here, after every cog has finished loading.
        self.tree.add_command(pulsereact_group)

        # Global handler for errors raised inside slash commands.
        self.tree.on_error = self._on_app_command_error

    async def on_ready(self) -> None:
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} server(s)")

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """
        Global handler for prefix command errors (currently just kick!sync).
        """
        if isinstance(error, commands.CommandNotFound):
            # Silently ignore unknown kick! commands instead of spamming errors.
            return

        if isinstance(error, commands.NotOwner):
            await ctx.reply("Only the bot owner can use this command.")
            return

        logger.error(f"Prefix command error in '{ctx.command}': {error}\n{traceback.format_exc()}")
        await ctx.reply("Something went wrong while running that command.")

    async def _on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """
        Global handler for slash command errors. Individual cogs can still
        catch specific errors themselves, this is the fallback so a user
        never sees a raw traceback or a stuck "thinking" state.
        """
        logger.error(
            f"Slash command error in '{interaction.command}': {error}\n{traceback.format_exc()}"
        )

        # Import here (not top-level) to avoid a circular import, since
        # utils.checks imports nothing from client.py but keeping this
        # local keeps the dependency direction obvious.
        from bot.utils.checks import DatabaseUnavailableError, GuildDisabledError

        if isinstance(error, GuildDisabledError):
            error_message = (
                "PulseReact is disabled in this server. "
                "Ask an admin to run `/pulsereact toggle` to re-enable it."
            )
        elif isinstance(error, DatabaseUnavailableError):
            error_message = "Could not verify bot status right now, try again in a moment."
        elif isinstance(error, app_commands.MissingPermissions):
            error_message = "You need the **Manage Server** permission to use this command."
        elif isinstance(error, app_commands.CheckFailure):
            error_message = str(error) or "You are not allowed to use this command here."
        else:
            error_message = "Something went wrong while running that command."

        # If the interaction already got a response (e.g. deferred), edit it.
        # Otherwise send a fresh ephemeral reply.
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)
