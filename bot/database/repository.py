"""
All Supabase queries live here. Cogs should never call the Supabase
client directly, they call these functions instead. Keeps DB logic
in one place and makes it easy to swap the DB later if needed.

Every function raises the underlying exception after logging it,
callers (cogs) are expected to catch and show a user-friendly message.
"""

from bot.core.logger import get_logger
from bot.database.supabase_client import supabase

logger = get_logger("database.repository")

VALID_MESSAGE_TYPES = {"all", "text", "image", "link", "video", "file"}


# ---------- guilds ----------

def get_or_create_guild(guild_id: int) -> dict:
    """
    Fetches the guild row, creating it with enabled=True if it
    doesn't exist yet. This is called whenever we need to check
    a guild's enabled state.
    """
    try:
        result = supabase.table("guilds").select("*").eq("guild_id", guild_id).execute()

        if result.data:
            return result.data[0]

        # Guild not seen before, create a default row for it.
        insert_result = (
            supabase.table("guilds")
            .insert({"guild_id": guild_id, "enabled": True})
            .execute()
        )
        logger.info(f"Created new guild row for guild_id={guild_id}")
        return insert_result.data[0]

    except Exception:
        logger.exception(f"Failed to get_or_create_guild for guild_id={guild_id}")
        raise


def is_guild_enabled(guild_id: int) -> bool:
    """
    Convenience wrapper used by the permission check before every
    slash command runs (except /pulsereact toggle itself).
    """
    guild_row = get_or_create_guild(guild_id)
    return guild_row.get("enabled", True)


def set_guild_enabled(guild_id: int, enabled: bool) -> None:
    """
    Toggles the bot on/off for a specific guild. Uses upsert so it
    works even if the guild row somehow doesn't exist yet.
    """
    try:
        supabase.table("guilds").upsert(
            {"guild_id": guild_id, "enabled": enabled}
        ).execute()
        logger.info(f"Set guild_id={guild_id} enabled={enabled}")
    except Exception:
        logger.exception(f"Failed to set_guild_enabled for guild_id={guild_id}")
        raise


# ---------- autoreact_configs ----------

def add_autoreact_entries(
    guild_id: int, channel_id: int, emojis: list[str], message_type: str
) -> list[str]:
    """
    Adds one row per emoji for the given channel. Returns the list of
    emojis that were actually inserted (skips duplicates silently since
    the table has a unique constraint on guild_id+channel_id+emoji+type).
    """
    if message_type not in VALID_MESSAGE_TYPES:
        raise ValueError(f"Invalid message_type: {message_type}")

    inserted: list[str] = []
    try:
        for emoji in emojis:
            row = {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "emoji": emoji,
                "message_type": message_type,
            }
            # upsert with ignore_duplicates avoids a hard failure if the
            # same emoji+channel+type combo is added twice.
            result = (
                supabase.table("autoreact_configs")
                .upsert(row, on_conflict="guild_id,channel_id,emoji,message_type", ignore_duplicates=True)
                .execute()
            )
            if result.data:
                inserted.append(emoji)

        logger.info(
            f"Added autoreact entries for guild_id={guild_id} channel_id={channel_id}: {inserted}"
        )
        return inserted

    except Exception:
        logger.exception(f"Failed to add_autoreact_entries for guild_id={guild_id}")
        raise


def remove_autoreact_channel(guild_id: int, channel_id: int) -> int:
    """
    Removes every emoji entry for a channel (full channel removal).
    Returns the number of rows deleted.
    """
    try:
        result = (
            supabase.table("autoreact_configs")
            .delete()
            .eq("guild_id", guild_id)
            .eq("channel_id", channel_id)
            .execute()
        )
        deleted_count = len(result.data)
        logger.info(f"Removed channel_id={channel_id} for guild_id={guild_id}, {deleted_count} rows")
        return deleted_count
    except Exception:
        logger.exception(f"Failed to remove_autoreact_channel for guild_id={guild_id}")
        raise


def remove_autoreact_emojis(guild_id: int, channel_id: int, emojis: list[str]) -> int:
    """
    Removes specific emoji entries from a channel, leaving the rest intact.
    Returns the number of rows deleted.
    """
    try:
        result = (
            supabase.table("autoreact_configs")
            .delete()
            .eq("guild_id", guild_id)
            .eq("channel_id", channel_id)
            .in_("emoji", emojis)
            .execute()
        )
        deleted_count = len(result.data)
        logger.info(
            f"Removed emojis={emojis} from channel_id={channel_id} guild_id={guild_id}, {deleted_count} rows"
        )
        return deleted_count
    except Exception:
        logger.exception(f"Failed to remove_autoreact_emojis for guild_id={guild_id}")
        raise


def get_guild_config(guild_id: int) -> list[dict]:
    """
    Returns every autoreact row for a guild, used by /pulsereact autoreact
    config to display the full setup grouped by channel.
    """
    try:
        result = (
            supabase.table("autoreact_configs")
            .select("*")
            .eq("guild_id", guild_id)
            .execute()
        )
        return result.data
    except Exception:
        logger.exception(f"Failed to get_guild_config for guild_id={guild_id}")
        raise


def get_channel_config(guild_id: int, channel_id: int) -> list[dict]:
    """
    Returns autoreact rows for one specific channel, used by the
    on_message listener to decide which emojis to react with.
    """
    try:
        result = (
            supabase.table("autoreact_configs")
            .select("*")
            .eq("guild_id", guild_id)
            .eq("channel_id", channel_id)
            .execute()
        )
        return result.data
    except Exception:
        logger.exception(f"Failed to get_channel_config for guild_id={guild_id} channel_id={channel_id}")
        raise
