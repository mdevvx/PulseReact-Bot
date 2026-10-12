-- PulseReact schema setup.
-- Run this once in the Supabase SQL Editor of the NEW project, before
-- running scripts/migrate_data.py. Safe to re-run.

create schema if not exists pulsereact;

-- Tracks per-server enabled/disabled state
create table if not exists pulsereact.guilds (
    guild_id bigint primary key,
    enabled boolean not null default true,
    created_at timestamptz not null default now()
);

-- Stores auto-react configuration, one row per channel + emoji + message type
create table if not exists pulsereact.autoreact_configs (
    id bigint generated always as identity primary key,
    guild_id bigint not null references pulsereact.guilds(guild_id) on delete cascade,
    channel_id bigint not null,
    emoji text not null,
    message_type text not null check (message_type in ('all', 'text', 'image', 'link', 'video', 'file')),
    unique (guild_id, channel_id, emoji, message_type)
);

create index if not exists idx_autoreact_guild on pulsereact.autoreact_configs(guild_id);
create index if not exists idx_autoreact_channel on pulsereact.autoreact_configs(guild_id, channel_id);

-- The bot connects with the service_role key, which bypasses RLS.
-- RLS with no policies keeps anon/authenticated keys locked out.
alter table pulsereact.guilds enable row level security;
alter table pulsereact.autoreact_configs enable row level security;

-- Custom schemas get no grants by default, the Data API needs these.
grant usage on schema pulsereact to service_role;
grant all on all tables in schema pulsereact to service_role;
grant all on all sequences in schema pulsereact to service_role;
alter default privileges in schema pulsereact grant all on tables to service_role;
alter default privileges in schema pulsereact grant all on sequences to service_role;

-- Make the Data API pick up the new schema immediately.
notify pgrst, 'reload schema';
