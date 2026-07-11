"""
Entry point. Run with: python -m bot.main
"""

from bot.core.client import PulseReactBot
from bot.core.config import config
from bot.core.logger import get_logger

logger = get_logger("main")


def run() -> None:
    bot = PulseReactBot()
    try:
        bot.run(config.discord_token, log_handler=None)  # We use our own logger, not discord.py's.
    except Exception:
        logger.exception("Bot crashed on startup")


if __name__ == "__main__":
    run()
