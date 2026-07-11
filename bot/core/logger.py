"""
Centralized logger setup. Every module should use:
    from bot.core.logger import get_logger
    logger = get_logger(__name__)

This gives consistent formatting across the whole bot and writes
to both the console and a rotating log file.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# Directory where log files are stored, created if missing.
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "pulsereact.log")

os.makedirs(LOG_DIR, exist_ok=True)

# Shared formatter so console and file logs look the same.
_FORMATTER = logging.Formatter(
    fmt="[{asctime}] [{levelname:<8}] {name}: {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
)


def _build_root_logger() -> None:
    """
    Configures the root 'pulsereact' logger once. Individual module
    loggers created via get_logger() inherit these handlers, so we
    don't attach handlers repeatedly for every module.
    """
    root_logger = logging.getLogger("pulsereact")
    root_logger.setLevel(logging.INFO)

    # Avoid attaching duplicate handlers if this runs more than once
    # (e.g. during cog reloads).
    if root_logger.handlers:
        return

    # Console output.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(_FORMATTER)
    root_logger.addHandler(console_handler)

    # File output, rotates at 5MB, keeps 3 backups so logs don't grow forever.
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(_FORMATTER)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a module-specific logger nested under 'pulsereact', e.g.
    'pulsereact.cogs.autoreact'. This makes it easy to trace which
    module a log line came from.
    """
    _build_root_logger()
    return logging.getLogger(f"pulsereact.{name}")
