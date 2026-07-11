"""
Parses the space-separated 'emojis' string from slash command input
into a list of valid emoji tokens, filtering out anything that isn't
actually an emoji (unicode or Discord custom emoji).
"""

import re

import emoji as emoji_lib

# Matches Discord custom emoji format, e.g. <:name:123456789012345678>
# or animated <a:name:123456789012345678>
CUSTOM_EMOJI_PATTERN = re.compile(r"^<a?:\w+:\d+>$")


def parse_emojis(raw: str) -> tuple[list[str], list[str]]:
    """
    Splits the raw input on whitespace and separates it into
    (valid_emojis, invalid_tokens). Invalid tokens are skipped rather
    than failing the whole command, per the agreed behavior.
    """
    tokens = raw.split()
    valid: list[str] = []
    invalid: list[str] = []

    for token in tokens:
        if CUSTOM_EMOJI_PATTERN.match(token) or emoji_lib.is_emoji(token):
            # Avoid accidental duplicates within the same command call.
            if token not in valid:
                valid.append(token)
        else:
            invalid.append(token)

    return valid, invalid
