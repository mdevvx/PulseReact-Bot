"""
Initializes a single shared Supabase client instance.
Import `supabase` from here anywhere a DB call is needed, never
create a new client elsewhere.
"""

from supabase import Client, create_client

from bot.core.config import config
from bot.core.logger import get_logger

logger = get_logger("database.supabase_client")

try:
    supabase: Client = create_client(config.supabase_url, config.supabase_key)
    logger.info("Supabase client initialized")
except Exception:
    logger.exception("Failed to initialize Supabase client")
    raise
