from evennia.utils.evtable import EvTable
from evennia import CmdSet
from .command import Command
from world.areas import Area, get_areas, save_area, update_area, find_area
from olc.base import OLCValidator


class AreaValidator(OLCValidator):
    """Simple validator for area data."""

    def validate(self, data: dict) -> list[str]:  # type: ignore[override]
        warnings: list[str] = []
        start = data.get("start")
        end = data.get("end")
        if start is not None and end is not None and start > end:
            warnings.append("Start VNUM greater than end; values swapped.")
        return warnings


class CmdAList(Command):
    """List defined areas."""

    key = "alist"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        areas = get_areas()
        if not areas:
            self.msg("No areas defined.")
            return
        table = EvTable("Name", "Range", "Builders", "Flags", "Age", "Interval", border="cells")
        for area in areas:
            table.add_row(
                area.key,
                f"{area.start}-{area.end}",
                ", ".join(area.builders),
                ", ".join(area.flags),
                str(area.age),
                str(area.reset_interval),
            )
        self.msg(str(table))


class CmdASave(Command):
    """Save changed areas."""

    key = "asave"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if self.args.strip().lower() != "changed":
            self.msg("Usage: asave changed")
            return
        # prototypes are written immediately on edit, so nothing to do
        self.msg("All areas saved.")


class CmdAEdit(Command):
    """Edit or create area metadata."""

    key = "aedit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg(
                "Usage: aedit create <name> <start> <end> | "
                "aedit range <name> <start> <end> | "
                "aedit builders <name> <list> | aedit flags <name> <list> | "
                "aedit interval <name> <ticks>"
            )
            return
        parts = self.args.split(None, 1)
        sub = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        if sub == "create":
            args = rest.split()
            if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
                self.msg("Usage: aedit create <name> <start> <end>")
                return
            name = args[0]
            start_val, end_val = int(args[1]), int(args[2])
            for warn in AreaValidator().validate({"start": start_val, "end": end_val}):
                self.msg(warn)
            start, end = min(start_val, end_val), max(start_val, end_val)
            if find_area(name)[1]:
                self.msg("Area already exists.")
                return
            area = Area(key=name, start=min(start, end), end=max(start, end))
            save_area(area)
            self.msg(f"Area {name} created.")
            return
        if sub == "range":
            args = rest.split()
            if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
                self.msg("Usage: aedit range <name> <start> <end>")
                return
            name = args[0]
            idx, area = find_area(name)
            if area is None:
                self.msg("Unknown area.")
                return
            start_val, end_val = int(args[1]), int(args[2])
            for warn in AreaValidator().validate({"start": start_val, "end": end_val}):
                self.msg(warn)
            area.start, area.end = min(start_val, end_val), max(start_val, end_val)
            update_area(idx, area)
            self.msg("Range updated.")
            return
        if sub == "builders":
            args = rest.split(None, 1)
            if len(args) != 2:
                self.msg("Usage: aedit builders <name> <builders>")
                return
            name, builders = args[0], args[1]
            idx, area = find_area(name)
            if area is None:
                self.msg("Unknown area.")
                return
            area.builders = [b.strip() for b in builders.split(',') if b.strip()]
            update_area(idx, area)
            self.msg("Builders updated.")
            return
        if sub == "interval":
            args = rest.split()
            if len(args) != 2 or not args[1].isdigit():
                self.msg("Usage: aedit interval <name> <ticks>")
                return
            name, val = args[0], int(args[1])
            idx, area = find_area(name)
            if area is None:
                self.msg("Unknown area.")
                return
            area.reset_interval = val
            update_area(idx, area)
            self.msg("Reset interval updated.")
            return
        if sub == "flags":
            args = rest.split(None, 1)
            if len(args) != 2:
                self.msg("Usage: aedit flags <name> <flags>")
                return
            name, flags = args[0], args[1]
            idx, area = find_area(name)
            if area is None:
                self.msg("Unknown area.")
                return
            area.flags = [f.strip().lower() for f in flags.split(',') if f.strip()]
            update_area(idx, area)
            self.msg("Flags updated.")
            return
        self.msg("Unknown subcommand.")


class CmdAreaReset(Command):
    """Reset an area's age."""

    key = "reset"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: reset <area>")
            return
        idx, area = find_area(self.args.strip())
        if area is None:
            self.msg("Unknown area.")
            return
        area.age = 0
        update_area(idx, area)
        self.msg(f"{area.key} reset.")


class CmdAreaAge(Command):
    """Show an area's age."""

    key = "age"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        target = self.args.strip()
        if not target and self.caller.location:
            target = self.caller.location.db.area or ""
        if not target:
            self.msg("Usage: age <area>")
            return
        _, area = find_area(target)
        if area is None:
            self.msg("Unknown area.")
            return
        self.msg(f"{area.key} age: {area.age}")


class AreaEditCmdSet(CmdSet):
    """CmdSet adding area editing commands."""

    key = "AreaEditCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdAList)
        self.add(CmdASave)
        self.add(CmdAEdit)
        self.add(CmdAreaReset)
        self.add(CmdAreaAge)

