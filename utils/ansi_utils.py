import re


def format_ansi_title(name: str) -> str:
    """Return ``name`` title-cased while preserving Evennia ANSI codes."""
    tokens = re.split(r'(\|.)', str(name))
    return "".join(token if token.startswith("|") else token.title() for token in tokens)

