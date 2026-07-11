"""
/pulsereact status
Shows bot health info: latency, uptime, total server count, and
whether the bot is enabled in the current server.

Deliberately does NOT use guild_enabled_check, status should still be
viewable even if the bot has been disabled for the server, otherwise
there'd be no way to confirm it's actually off.
"""

from datetime import datetime, timezone

import discord
from discord.ext import commands

from bot.cogs.group import pulsereact_group
from bot.core.logger import get_logger
from bot.database import repository
from bot.utils.embeds import error_embed, info_embed

logger = get_logger("cogs.general.status")


def _format_uptime(start_time: datetime) -> str:
    """
    Converts the time since bot startup into a readable "Xd Xh Xm Xs" string.
    """
    delta = datetime.now(timezone.utc) - start_time
    total_seconds = int(delta.total_seconds())

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")

    return " ".join(parts)


@pulsereact_group.command(name="status", description="Shows PulseReact's current status and stats.")
async def status(interaction: discord.Interaction) -> None:
    bot = interaction.client
    latency_ms = round(bot.latency * 1000, 1)
    uptime_str = _format_uptime(bot.start_time)
    server_count = len(bot.guilds)

    # Look up whether the bot is enabled specifically in this server.
    guild_status_line = "Not applicable (used outside a server)"
    if interaction.guild_id is not None:
        try:
            enabled = repository.is_guild_enabled(interaction.guild_id)
            guild_status_line = "🟢 Enabled" if enabled else "🔴 Disabled"
        except Exception:
            logger.exception(f"Failed to fetch guild status for guild_id={interaction.guild_id}")
            await interaction.response.send_message(
                embed=error_embed("Status Unavailable", "Could not reach the database right now."),
                ephemeral=True,
            )
            return

    embed = info_embed("📊 PulseReact Status")
    embed.add_field(name="Latency", value=f"{latency_ms} ms", inline=True)
    embed.add_field(name="Uptime", value=uptime_str, inline=True)
    embed.add_field(name="Servers", value=str(server_count), inline=True)
    embed.add_field(name="This Server", value=guild_status_line, inline=False)

    await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    # No Cog class needed here, /pulsereact status is already attached
    # to pulsereact_group via the decorator above at module import time.
    logger.info("Status command ready")
