"""
Owner-only prefix command to sync slash commands globally.
Global syncs can take up to an hour to propagate on Discord's side,
so this is meant to be run manually after deploying command changes,
not on every startup.
"""

from discord.ext import commands

from bot.core.logger import get_logger

logger = get_logger("cogs.owner.sync")


class SyncCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx: commands.Context) -> None:
        """
        !sync
        Syncs all slash commands globally with Discord.
        Restricted to the bot owner via commands.is_owner().
        """
        try:
            synced_commands = await self.bot.tree.sync()
            logger.info(f"Synced {len(synced_commands)} slash command(s) globally")
            await ctx.reply(
                f"Synced {len(synced_commands)} slash command(s) globally. "
                "This can take up to an hour to appear in all servers."
            )
        except Exception:
            logger.exception("Failed to sync slash commands")
            await ctx.reply("Sync failed, check the logs for details.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SyncCog(bot))
