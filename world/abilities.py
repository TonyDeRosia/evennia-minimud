from utils.ansi_utils import format_ansi_title


def colorize_name(name: str, color: str = "c") -> str:
    """Return ``name`` capitalized and wrapped in ANSI color codes."""
    return f"|{color}{format_ansi_title(name)}|n"
