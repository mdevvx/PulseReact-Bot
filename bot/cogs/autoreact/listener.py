"""
Core auto-react listener. Fires on every message across every server
the bot is in, checks that server's config, and reacts with whatever
emojis match the message's type in that channel.

Reacts to messages from any author, including other bots, the only
exception is skipping the bot's own messages to avoid reacting to itself.
"""

import asyncio
import re

import discord
from discord.ext import commands

from bot.core.logger import get_logger
from bot.database import repository

logger = get_logger("cogs.autoreact.listener")

URL_PATTERN = re.compile(r"https?://\S+")

# Small delay between consecutive reactions on the same message to stay
# well clear of Discord's rate limits when many emojis are configured.
REACTION_DELAY_SECONDS = 0.25


class AutoReactListener(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _detect_message_types(self, message: discord.Message) -> set[str]:
        """
        Returns the set of message types this message matches. A message
        can match more than one type (e.g. text with a link), that's fine,
        every matching row's emoji will be applied.
        """
        types: set[str] = set()

        has_content = bool(message.content and message.content.strip())
        has_attachments = bool(message.attachments)
        has_embeds = bool(message.embeds)

        # text: has content, no attachments/embeds attached alongside it.
        if has_content and not has_attachments and not has_embeds:
            types.add("text")

        # image: any attachment or embed that is an image.
        if any(
            att.content_type and att.content_type.startswith("image/") for att in message.attachments
        ) or any(embed.type == "image" for embed in message.embeds):
            types.add("image")

        # video: any attachment or embed that is a video.
        if any(
            att.content_type and att.content_type.startswith("video/") for att in message.attachments
        ) or any(embed.type == "video" for embed in message.embeds):
            types.add("video")

        # link: a URL in the message text, or a link-type embed.
        if (has_content and URL_PATTERN.search(message.content)) or any(
            embed.type == "link" for embed in message.embeds
        ):
            types.add("link")

        # file: an attachment that isn't image or video (pdf, zip, etc).
        if any(
            not (att.content_type and (att.content_type.startswith("image/") or att.content_type.startswith("video/")))
            for att in message.attachments
        ):
            types.add("file")

        return types

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Ignore DMs, this bot is server-only.
        if message.guild is None:
            return

        # Never react to the bot's own messages, avoids potential loops.
        if message.author.id == self.bot.user.id:
            return

        # Note: deliberately NOT checking message.author.bot here, per
        # requirements the bot reacts to messages from other bots too.

        try:
            if not repository.is_guild_enabled(message.guild.id):
                return
        except Exception:
            logger.exception(f"Failed to check guild enabled state for guild_id={message.guild.id}")
            return

        try:
            config_rows = repository.get_channel_config(message.guild.id, message.channel.id)
        except Exception:
            logger.exception(
                f"Failed to fetch channel config for guild_id={message.guild.id} channel_id={message.channel.id}"
            )
            return

        if not config_rows:
            # No auto-react configured for this channel, nothing to do.
            return

        matched_types = self._detect_message_types(message)

        # Collect emojis whose configured type matches this message,
        # 'all' always matches regardless of detected types.
        emojis_to_react: list[str] = [
            row["emoji"]
            for row in config_rows
            if row["message_type"] == "all" or row["message_type"] in matched_types
        ]

        for emoji_str in emojis_to_react:
            try:
                # PartialEmoji.from_str handles both unicode emojis and
                # Discord custom emoji strings like <:name:id>.
                emoji = discord.PartialEmoji.from_str(emoji_str)
                await message.add_reaction(emoji)
            except discord.HTTPException:
                # Covers unknown/deleted custom emoji, missing permissions,
                # or rate limiting. Log and move on to the next emoji
                # rather than aborting the whole batch.
                logger.warning(
                    f"Failed to react with {emoji_str} on message {message.id} in guild {message.guild.id}"
                )
            await asyncio.sleep(REACTION_DELAY_SECONDS)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoReactListener(bot))
