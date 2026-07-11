"""
Reusable checks for slash commands. The main one here blocks every
slash command from running if the bot has been disabled for that
server via /pulsereact toggle, except /pulsereact toggle itself so
an admin can always re-enable it.
"""

import discord
from discord import app_commands

from bot.core.logger import get_logger
from bot.database import repository

logger = get_logger("utils.checks")


class GuildDisabledError(app_commands.CheckFailure):
    """
    Raised when a command is used in a server where the bot has been
    disabled via /pulsereact toggle. Handled specifically in the
    global error handler in core/client.py.
    """
    pass


class DatabaseUnavailableError(app_commands.CheckFailure):
    """
    Raised when the enabled/disabled check itself fails to reach Supabase.
    """
    pass


def guild_enabled_check():
    """
    Decorator applied to every slash command except toggle.
    Usage: @guild_enabled_check()
    Place it above the command function, below @app_commands.command().

    Raises instead of responding directly, so the global error handler
    in client.py is the single place that sends a message back to the
    user, avoiding double responses.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild_id is None:
            raise app_commands.CheckFailure("This command can only be used inside a server.")

        try:
            enabled = repository.is_guild_enabled(interaction.guild_id)
        except Exception:
            logger.exception(f"guild_enabled_check failed for guild_id={interaction.guild_id}")
            raise DatabaseUnavailableError()

        if not enabled:
            raise GuildDisabledError()

        return True

    return app_commands.check(predicate)
