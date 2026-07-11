# PulseReact

A Discord bot with a fully configurable, per-server auto-react system, backed by Supabase.

## Features

- Auto-reacts to messages in any number of channels, with any number of emojis per channel
- Filter reactions by message type: all, text, image, link, video, file
- Reacts to messages from any user or bot (except itself)
- `/pulsereact toggle` to fully enable/disable the bot per server, independently of every other server
- `/pulsereact status` to check bot health (latency, uptime, server count)
- `kick!sync` owner-only command to sync slash commands globally

## 1. Supabase setup

Create a new Supabase project, then run this SQL in the Supabase SQL Editor to create the required tables.

```sql
-- Tracks per-server enabled/disabled state
create table guilds (
    guild_id bigint primary key,
    enabled boolean not null default true,
    created_at timestamptz not null default now()
);

-- Stores auto-react configuration, one row per channel + emoji + message type
create table autoreact_configs (
    id bigint generated always as identity primary key,
    guild_id bigint not null references guilds(guild_id) on delete cascade,
    channel_id bigint not null,
    emoji text not null,
    message_type text not null check (message_type in ('all', 'text', 'image', 'link', 'video', 'file')),
    unique (guild_id, channel_id, emoji, message_type)
);

create index idx_autoreact_guild on autoreact_configs(guild_id);
create index idx_autoreact_channel on autoreact_configs(guild_id, channel_id);
```

From your Supabase project settings, grab the **Project URL** and the **service_role key** (not the anon key, since the bot needs full read/write access from a trusted server environment).

## 2. Discord application setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application.
2. Under **Bot**, create a bot user and copy the token.
3. Under **Bot**, enable the **Message Content Intent**. This is required for the auto-react message type detection.
4. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, and under bot permissions select at minimum:
   - View Channels
   - Send Messages
   - Add Reactions
   - Read Message History
5. Use the generated URL to invite the bot to a server. Repeat for each server, the bot works independently per server with no shared state.

Your own Discord user ID (for `OWNER_ID`) can be copied by enabling Developer Mode in Discord settings, then right-clicking your profile and selecting "Copy User ID".

## 3. Environment setup

Copy `.env.example` to `.env` and fill in the values.

```
DISCORD_TOKEN=your_bot_token
OWNER_ID=your_discord_user_id
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
```

## 4. Install and run

```bash
pip install -r requirements.txt
python -m bot.main
```

Once the bot is online, DM it or use it in a server as the owner and run:

```
kick!sync
```

This registers all slash commands globally. It can take up to an hour to appear everywhere the first time, subsequent syncs after further command changes will also need `kick!sync` run again.

## Commands

| Command | Access | Description |
|---|---|---|
| `kick!sync` | Owner only | Syncs slash commands globally |
| `/pulsereact status` | Everyone | Shows bot status |
| `/pulsereact toggle` | Manage Server | Enables/disables PulseReact for this server |
| `/pulsereact autoreact add` | Manage Server | Adds emojis to a channel with a message type filter |
| `/pulsereact autoreact remove` | Manage Server | Removes a channel or specific emojis from it |
| `/pulsereact autoreact config` | Everyone | Shows current auto-react configuration |

## Project structure

```
bot/
├── main.py                 # Entry point
├── core/                   # Config, logger, bot client
├── cogs/
│   ├── group.py            # Shared /pulsereact command group
│   ├── owner/sync.py        # kick!sync
│   ├── general/status.py    # /pulsereact status
│   ├── admin/toggle.py       # /pulsereact toggle
│   └── autoreact/
│       ├── commands.py      # add/remove/config commands
│       └── listener.py      # on_message auto-react handler
├── database/                # Supabase client and query functions
└── utils/                   # Checks, embeds, emoji parsing
```

## Notes

- Logs are written to `logs/pulsereact.log` (rotates at 5MB, keeps 3 backups) in addition to the console.
- Each server's data is fully isolated by `guild_id`, adding the bot to a new server starts with a clean, independent configuration.
