"""
One-off data migration from the old Supabase project to the new one.

Copies guilds and autoreact_configs from OLD (public schema by default)
into NEW (pulsereact schema by default). Run sql/001_pulsereact_schema.sql
on the new project first, and add "pulsereact" to its exposed schemas.

Idempotent: guilds are upserted on guild_id and autoreact rows skip
duplicates, so running it twice won't duplicate anything.

Required env vars (can live in .env):
    OLD_SUPABASE_URL, OLD_SUPABASE_KEY
    NEW_SUPABASE_URL, NEW_SUPABASE_KEY
Optional:
    OLD_SUPABASE_SCHEMA (default: public)
    NEW_SUPABASE_SCHEMA (default: pulsereact)

Usage:
    python -m scripts.migrate_data
"""

import os
import sys

from dotenv import load_dotenv
from supabase import Client, ClientOptions, create_client

load_dotenv()

PAGE_SIZE = 1000
BATCH_SIZE = 500


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        print(f"[MIGRATE ERROR] Missing required environment variable: {key}")
        sys.exit(1)
    return value


def _client(prefix: str, default_schema: str) -> tuple[Client, str]:
    schema = os.getenv(f"{prefix}_SUPABASE_SCHEMA", default_schema)
    client = create_client(
        _require(f"{prefix}_SUPABASE_URL"),
        _require(f"{prefix}_SUPABASE_KEY"),
        options=ClientOptions(schema=schema),
    )
    return client, schema


def _fetch_all(client: Client, table: str, order_by: str) -> list[dict]:
    """Reads every row, paging past the Data API's default row limit."""
    rows: list[dict] = []
    start = 0
    while True:
        page = (
            client.table(table)
            .select("*")
            .order(order_by)
            .range(start, start + PAGE_SIZE - 1)
            .execute()
            .data
        )
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def _count(client: Client, table: str) -> int:
    return client.table(table).select("*", count="exact").limit(1).execute().count


def main() -> None:
    old, old_schema = _client("OLD", "public")
    new, new_schema = _client("NEW", "pulsereact")
    print(f"Migrating {old_schema} (old project) -> {new_schema} (new project)")

    guilds = _fetch_all(old, "guilds", "guild_id")
    configs = _fetch_all(old, "autoreact_configs", "id")
    print(f"Read {len(guilds)} guilds, {len(configs)} autoreact_configs")

    # Guilds first, autoreact_configs has a foreign key to them.
    for i in range(0, len(guilds), BATCH_SIZE):
        new.table("guilds").upsert(guilds[i:i + BATCH_SIZE], on_conflict="guild_id").execute()

    # id is an identity column in the new table, let it generate fresh ones.
    config_rows = [
        {k: row[k] for k in ("guild_id", "channel_id", "emoji", "message_type")}
        for row in configs
    ]
    for i in range(0, len(config_rows), BATCH_SIZE):
        new.table("autoreact_configs").upsert(
            config_rows[i:i + BATCH_SIZE],
            on_conflict="guild_id,channel_id,emoji,message_type",
            ignore_duplicates=True,
        ).execute()

    new_guilds = _count(new, "guilds")
    new_configs = _count(new, "autoreact_configs")
    print(f"New project now has {new_guilds} guilds, {new_configs} autoreact_configs")

    if new_guilds < len(guilds) or new_configs < len(configs):
        print("[MIGRATE ERROR] Row counts in the new project are lower than the old one")
        sys.exit(1)
    print("Migration complete")


if __name__ == "__main__":
    main()
