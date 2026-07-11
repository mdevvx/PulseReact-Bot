"""
Shared slash command group definitions. All /pulsereact subcommands
across different cog files attach to these same Group instances,
so Discord shows one unified /pulsereact command with subcommands
and a nested /pulsereact autoreact subgroup.

This module must be imported before any cog that adds commands to
these groups, and the groups are registered onto the bot's tree once
in client.py's setup_hook, after all cogs have loaded.
"""

from discord import app_commands

# Top-level group: /pulsereact
pulsereact_group = app_commands.Group(
    name="pulsereact",
    description="PulseReact bot commands",
)

# Nested group: /pulsereact autoreact
autoreact_group = app_commands.Group(
    name="autoreact",
    description="Configure auto-reactions for this server",
    parent=pulsereact_group,
)
