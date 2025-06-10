from evennia import create_object
from .command import Command
from utils import vnum_registry, mob_proto
from world import prototypes, area_npcs


def builder_cnpc_prompt(caller, name):
    """Interactively create an NPC."""
    desc = yield (f"Enter a description for {name}:")
    race = yield ("Race:")
    combat_class = yield ("Combat class:")
    level_in = yield ("Level:")
    try:
        level = int(level_in)
    except ValueError:
        level = 1
    confirm = yield ("Create NPC? Yes/No")
    if confirm.strip().lower() not in ("yes", "y"):
        caller.msg("Cancelled.")
        return
    vnum = vnum_registry.get_next_vnum("npc")
    npc = create_object("typeclasses.npcs.BaseNPC", key=name, location=caller.location)
    npc.db.desc = desc
    npc.db.race = race
    npc.db.charclass = combat_class
    npc.db.level = level
    npc.db.vnum = vnum
    npc.tags.add(f"M{vnum}", category="vnum")
    proto = {
        "key": name,
        "typeclass": "typeclasses.npcs.BaseNPC",
        "desc": desc,
        "race": race,
        "npc_class": "base",
        "combat_class": combat_class,
        "level": level,
        "vnum": vnum,
    }
    prototypes.register_npc_prototype(name, proto)
    mob_proto.register_prototype(proto, vnum=vnum)
    if caller.location and caller.location.db.area:
        area_npcs.add_area_npc(caller.location.db.area, name)
    caller.msg(f"NPC {name} created with VNUM {vnum}.")


class CmdBuilderTypes(Command):
    """Access type-specific builder helpers."""

    key = "builder"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        args = self.args.strip()
        if not args:
            self.msg("Usage: builder types cnpc <name>")
            return
        parts = args.split(None, 2)
        if len(parts) < 3 or parts[0].lower() != "types":
            self.msg("Usage: builder types cnpc <name>")
            return
        sub = parts[1].lower()
        name = parts[2].strip()
        if sub == "cnpc" and name:
            builder_cnpc_prompt(self.caller, name)
        else:
            self.msg("Usage: builder types cnpc <name>")
