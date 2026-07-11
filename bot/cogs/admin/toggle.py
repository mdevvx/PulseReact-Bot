"""
/pulsereact toggle
Enables or disables PulseReact for the current server. Deliberately
does NOT use guild_enabled_check, this command must always work so
an admin can re-enable the bot after disabling it.

Restricted to members with the Manage Server permission.
"""

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.group import pulsereact_group
from bot.core.logger import get_logger
from bot.database import repository
from bot.utils.embeds import error_embed, success_embed

logger = get_logger("cogs.admin.toggle")


@pulsereact_group.command(name="toggle", description="Enable or disable PulseReact for this server.")
@app_commands.default_permissions(manage_guild=True)  # UI hint in Discord's integration settings.
@app_commands.checks.has_permissions(manage_guild=True)  # Actual runtime enforcement.
async def toggle(interaction: discord.Interaction) -> None:
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "This command can only be used inside a server.", ephemeral=True
        )
        return

    try:
        currently_enabled = repository.is_guild_enabled(interaction.guild_id)
        new_state = not currently_enabled
        repository.set_guild_enabled(interaction.guild_id, new_state)
    except Exception:
        logger.exception(f"Failed to toggle guild_id={interaction.guild_id}")
        await interaction.response.send_message(
            embed=error_embed("Toggle Failed", "Could not update the database, try again shortly."),
            ephemeral=True,
        )
        return

    state_text = "enabled" if new_state else "disabled"
    embed = success_embed("PulseReact Toggled", f"PulseReact is now **{state_text}** in this server.")
    await interaction.response.send_message(embed=embed)

    logger.info(f"Guild {interaction.guild_id} toggled to enabled={new_state} by user {interaction.user.id}")


async def setup(bot: commands.Bot) -> None:
    # No Cog class needed, /pulsereact toggle is already attached to
    # pulsereact_group via the decorator above at module import time.
    logger.info("Toggle command ready")
