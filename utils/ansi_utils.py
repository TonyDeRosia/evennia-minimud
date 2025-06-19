import re
from evennia.utils.ansi import strip_ansi


def ansi_pad(text: str, width: int, align: str = "c") -> str:
    """Return ``text`` padded to ``width`` while ignoring ANSI codes."""

    real_len = len(strip_ansi(text))
    pad_len = max(width - real_len, 0)
    if align == "l":
        return text + " " * pad_len
    if align == "r":
        return " " * pad_len + text
    left = pad_len // 2
    right = pad_len - left
    return " " * left + text + " " * right


def format_ansi_title(name: str) -> str:
    """Return ``name`` title-cased while preserving Evennia ANSI codes."""
    tokens = re.split(r'(\|.)', str(name))
    return "".join(token if token.startswith("|") else token.title() for token in tokens)

