"""
Loads and validates all environment variables needed by the bot.
Every other module should import the `config` instance from here
instead of calling os.getenv() directly. Keeps env access in one place.
"""

import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

# Load variables from .env into the process environment.
load_dotenv()


@dataclass(frozen=True)
class Config:
    """
    Immutable container for bot configuration.
    frozen=True prevents accidental overwrites at runtime.
    """
    discord_token: str
    owner_id: int
    supabase_url: str
    supabase_key: str
    supabase_schema: str


def _get_required_env(key: str) -> str:
    """
    Fetches an environment variable and exits the process with a clear
    error if it's missing. Failing fast here avoids confusing errors
    later during bot startup.
    """
    value = os.getenv(key)
    if not value:
        print(f"[CONFIG ERROR] Missing required environment variable: {key}")
        print("Check your .env file against .env.example")
        sys.exit(1)
    return value


def load_config() -> Config:
    """
    Builds and returns a validated Config object.
    Called once at startup in main.py.
    """
    owner_id_raw = _get_required_env("OWNER_ID")

    # OWNER_ID must be a valid Discord snowflake (integer).
    try:
        owner_id = int(owner_id_raw)
    except ValueError:
        print("[CONFIG ERROR] OWNER_ID must be a numeric Discord user ID")
        sys.exit(1)

    return Config(
        discord_token=_get_required_env("DISCORD_TOKEN"),
        owner_id=owner_id,
        supabase_url=_get_required_env("SUPABASE_URL"),
        supabase_key=_get_required_env("SUPABASE_KEY"),
        # Tables live in a dedicated schema, not public.
        supabase_schema=os.getenv("SUPABASE_SCHEMA") or "pulsereact",
    )


# Single shared config instance, import this everywhere else.
config = load_config()
