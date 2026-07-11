"""
/pulsereact autoreact add
/pulsereact autoreact remove
/pulsereact autoreact config

Lets server admins configure which channels get auto-reacted to,
with which emojis, and for which message types. All three commands
are blocked while the bot is disabled for the server (guild_enabled_check).
"""

from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.group import autoreact_group
from bot.core.logger import get_logger
from bot.database import repository
from bot.utils.checks import guild_enabled_check
from bot.utils.embeds import error_embed, info_embed, success_embed
from bot.utils.emoji_utils import parse_emojis

logger = get_logger("cogs.autoreact.commands")

# Using Literal here makes discord.py auto-generate a dropdown of choices
# for the 'type' parameter, no manual app_commands.Choice list needed.
MessageType = Literal["all", "text", "image", "link", "video", "file"]


@autoreact_group.command(name="add", description="Add auto-react emojis to a channel.")
@app_commands.describe(
    channel="The channel to auto-react in",
    emojis="One or more emojis separated by spaces, e.g. 👍 🔥 ✅",
    type="Which message types should trigger these emojis",
)
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
@guild_enabled_check()
async def add(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    emojis: str,
    type: MessageType = "all",
) -> None:
    valid_emojis, invalid_tokens = parse_emojis(emojis)

    if not valid_emojis:
        await interaction.response.send_message(
            embed=error_embed(
                "No Valid Emojis Found",
                "None of the input looked like a valid emoji. Try again with real emojis, e.g. 👍 🔥",
            ),
            ephemeral=True,
        )
        return

    try:
        inserted = repository.add_autoreact_entries(
            guild_id=interaction.guild_id,
            channel_id=channel.id,
            emojis=valid_emojis,
            message_type=type,
        )
    except Exception:
        logger.exception(f"Failed to add autoreact entries for guild_id={interaction.guild_id}")
        await interaction.response.send_message(
            embed=error_embed("Add Failed", "Could not save this to the database, try again shortly."),
            ephemeral=True,
        )
        return

    description_lines = [f"Channel: {channel.mention}", f"Message type: **{type}**"]
    if inserted:
        description_lines.append(f"Added: {' '.join(inserted)}")
    if invalid_tokens:
        description_lines.append(f"Skipped invalid input: {' '.join(invalid_tokens)}")
    if len(inserted) < len(valid_emojis):
        description_lines.append("Some emojis were already configured for this channel and type.")

    embed = success_embed("Auto-React Updated", "\n".join(description_lines))
    await interaction.response.send_message(embed=embed)


@autoreact_group.command(name="remove", description="Remove auto-react emojis from a channel.")
@app_commands.describe(
    channel="The channel to remove auto-react config from",
    emojis="Specific emojis to remove, separated by spaces. Leave empty to remove the whole channel.",
)
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
@guild_enabled_check()
async def remove(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    emojis: str = "",
) -> None:
    try:
        if emojis.strip():
            valid_emojis, invalid_tokens = parse_emojis(emojis)
            if not valid_emojis:
                await interaction.response.send_message(
                    embed=error_embed("No Valid Emojis Found", "None of the input looked like a valid emoji."),
                    ephemeral=True,
                )
                return

            deleted_count = repository.remove_autoreact_emojis(
                guild_id=interaction.guild_id, channel_id=channel.id, emojis=valid_emojis
            )
            description = f"Removed {deleted_count} emoji entr{'y' if deleted_count == 1 else 'ies'} from {channel.mention}."
        else:
            deleted_count = repository.remove_autoreact_channel(
                guild_id=interaction.guild_id, channel_id=channel.id
            )
            description = f"Removed all auto-react config from {channel.mention} ({deleted_count} entries)."

    except Exception:
        logger.exception(f"Failed to remove autoreact entries for guild_id={interaction.guild_id}")
        await interaction.response.send_message(
            embed=error_embed("Remove Failed", "Could not update the database, try again shortly."),
            ephemeral=True,
        )
        return

    await interaction.response.send_message(embed=success_embed("Auto-React Updated", description))


@autoreact_group.command(name="config", description="View all auto-react configuration for this server.")
@guild_enabled_check()
async def config(interaction: discord.Interaction) -> None:
    try:
        rows = repository.get_guild_config(interaction.guild_id)
    except Exception:
        logger.exception(f"Failed to fetch config for guild_id={interaction.guild_id}")
        await interaction.response.send_message(
            embed=error_embed("Could Not Load Config", "Could not reach the database right now."),
            ephemeral=True,
        )
        return

    if not rows:
        await interaction.response.send_message(
            embed=info_embed("Auto-React Config", "No channels are configured yet. Use `/pulsereact autoreact add` to set one up.")
        )
        return

    # Group rows by channel, then by message type within each channel, so
    # each line reads as "all the emojis for one type" instead of one
    # line per emoji (which gets very long when many emojis share a type).
    grouped: dict[int, dict[str, list[str]]] = {}
    for row in rows:
        by_type = grouped.setdefault(row["channel_id"], {})
        by_type.setdefault(row["message_type"], []).append(row["emoji"])

    embed = info_embed("⚙️ Auto-React Configuration")
    for channel_id, by_type in grouped.items():
        lines = [
            f"**{message_type}** — {' '.join(emojis)}"
            for message_type, emojis in by_type.items()
        ]
        embed.add_field(name=f"<#{channel_id}>", value="\n".join(lines), inline=False)

    await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    # No Cog class needed, all three commands are already attached to
    # autoreact_group via decorators above at module import time.
    logger.info("Autoreact commands ready")
