import re
from evennia.utils import iter_to_str

_color_strip_re = re.compile(r"\|.")


def _strip(text: str) -> str:
    """Remove simple Evennia color codes for width calculations."""
    return _color_strip_re.sub("", text)


def _pad(text: str, width: int) -> str:
    """Pad ``text`` with spaces to ``width`` accounting for color codes."""
    return text + " " * (width - len(_strip(text)))


INTERACTIVE_CMDSETS = {"Gather CmdSet", "Interact CmdSet"}


def _is_interactive(obj) -> bool:
    """Return True if ``obj`` should be displayed as an interactive object."""
    try:
        for key in INTERACTIVE_CMDSETS:
            if obj.cmdset.has_cmdset(key, must_be_default=True):
                return True
    except Exception:
        pass
    return hasattr(obj, "at_gather")


def get_room_display(room, looker) -> str:
    """Return a boxed display of ``room`` as seen by ``looker``."""

    lines = []

    if header := room.get_display_header(looker):
        lines.append(header)

    lines.append(room.get_display_name(looker))

    if desc := room.get_display_desc(looker):
        lines.append(desc)

    if exits := room.get_display_exits(looker):
        lines.append(exits)

    players = []
    npcs = []
    items = []
    interactive = []

    for char in room.filter_visible(room.contents_get(content_type="character"), looker):
        name = char.get_display_name(looker)
        if char.account:
            players.append(name)
        else:
            npcs.append(name)

    for obj in room.filter_visible(room.contents_get(content_type="object"), looker):
        name = obj.get_display_name(looker)
        if _is_interactive(obj):
            interactive.append(name)
        else:
            items.append(name)

    if players:
        lines.append(f"|wPlayers:|n {iter_to_str(players)}")
    if npcs:
        lines.append(f"|wNPCs:|n {iter_to_str(npcs)}")
    if items:
        lines.append(f"|wItems:|n {iter_to_str(items)}")
    if interactive:
        lines.append(f"|wInteractive:|n {iter_to_str(interactive)}")

    if footer := room.get_display_footer(looker):
        lines.append(footer)

    width = max(len(_strip(l)) for l in lines) if lines else 0
    top = "╔" + "═" * (width + 2) + "╗"
    bottom = "╚" + "═" * (width + 2) + "╝"

    out = [top]
    for line in lines:
        out.append("║ " + _pad(line, width) + " ║")
    out.append(bottom)

    return "\n".join(out)
