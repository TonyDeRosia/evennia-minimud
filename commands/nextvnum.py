from .command import Command
from utils import vnum_registry


class CmdNextVnum(Command):
    """Return the next available VNUM for a category."""

    key = "@nextvnum"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        arg = self.args.strip().upper()
        if arg not in {"I", "M", "R", "O", "Q", "S"}:
            self.msg("Usage: @nextvnum <I|M|R|O|Q|S>")
            return

        category_map = {
            "M": "npc",
            "I": "object",
            "O": "object",
            "R": "room",
            "Q": "quest",
            "S": "script",
        }
        category = category_map[arg]
        try:
            vnum = vnum_registry.get_next_vnum(category)
        except KeyError:
            self.msg("Unsupported VNUM category.")
            return
        self.msg(str(vnum))

