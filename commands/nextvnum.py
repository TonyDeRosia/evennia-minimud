from .command import Command
from utils import vnum_registry
from world.areas import get_area_vnum_range


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


class CmdListVnums(Command):
    """List a few unused VNUMs for a category or area."""

    key = "@listvnums"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @listvnums <npc|room|object> [area]")
            return

        parts = self.args.split(None, 1)
        category = parts[0].lower()
        if category not in ("npc", "room", "object"):
            self.msg("Category must be npc, room, or object.")
            return

        area = parts[1].strip() if len(parts) > 1 else None
        start, end = vnum_registry.VNUM_RANGES[category]

        if area:
            rng = get_area_vnum_range(area)
            if not rng:
                self.msg("Area not found.")
                return
            start = max(start, rng[0])
            end = min(end, rng[1])
            if start > end:
                self.msg("Area range does not overlap with category range.")
                return

        free = []
        for num in range(start, end + 1):
            if vnum_registry.validate_vnum(num, category):
                free.append(num)
                if len(free) >= 5:
                    break

        if free:
            self.msg("Next free VNUMs: " + ", ".join(str(n) for n in free))
        else:
            self.msg("No free VNUMs found in range.")

