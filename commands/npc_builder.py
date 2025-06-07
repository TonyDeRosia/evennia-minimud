from evennia.utils.evmenu import EvMenu
from evennia import create_object
from typeclasses.characters import NPC
from utils.slots import SLOT_ORDER
from .command import Command


# Menu nodes for NPC creation

def menunode_desc(caller, raw_string="", **kwargs):
    text = "|wEnter a short description for the NPC:|n"
    options = {"key": "_default", "goto": _set_desc}
    return text, options

def _set_desc(caller, raw_string, **kwargs):
    caller.ndb.buildnpc["desc"] = raw_string.strip()
    return "menunode_npc_type"

def menunode_npc_type(caller, raw_string="", **kwargs):
    text = "|wEnter NPC type (e.g. merchant, guard):|n"
    options = {"key": "_default", "goto": _set_npc_type}
    return text, options

def _set_npc_type(caller, raw_string, **kwargs):
    caller.ndb.buildnpc["npc_type"] = raw_string.strip()
    return "menunode_creature_type"

def menunode_creature_type(caller, raw_string="", **kwargs):
    text = "|wCreature type (humanoid/quadruped/unique):|n"
    options = {"key": "_default", "goto": _set_creature_type}
    return text, options

def _set_creature_type(caller, raw_string, **kwargs):
    caller.ndb.buildnpc["creature_type"] = raw_string.strip().lower() or "humanoid"
    return "menunode_level"

def menunode_level(caller, raw_string="", **kwargs):
    text = "|wLevel of NPC:|n"
    options = {"key": "_default", "goto": _set_level}
    return text, options

def _set_level(caller, raw_string, **kwargs):
    try:
        caller.ndb.buildnpc["level"] = int(raw_string.strip())
    except ValueError:
        caller.msg("Enter a number.")
        return "menunode_level"
    return "menunode_resources"

def menunode_resources(caller, raw_string="", **kwargs):
    text = "|wEnter HP MP SP separated by spaces:|n"
    options = {"key": "_default", "goto": _set_resources}
    return text, options

def _set_resources(caller, raw_string, **kwargs):
    parts = raw_string.split()
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        caller.msg("Enter three numbers separated by spaces.")
        return "menunode_resources"
    caller.ndb.buildnpc["hp"] = int(parts[0])
    caller.ndb.buildnpc["mp"] = int(parts[1])
    caller.ndb.buildnpc["sp"] = int(parts[2])
    return "menunode_stats"

def menunode_stats(caller, raw_string="", **kwargs):
    text = "|wEnter STR CON DEX INT WIS LUCK separated by spaces:|n"
    options = {"key": "_default", "goto": _set_stats}
    return text, options

def _set_stats(caller, raw_string, **kwargs):
    parts = raw_string.split()
    if len(parts) != 6 or not all(p.isdigit() for p in parts):
        caller.msg("Enter six numbers separated by spaces.")
        return "menunode_stats"
    stats = ["STR", "CON", "DEX", "INT", "WIS", "LUCK"]
    caller.ndb.buildnpc["primary_stats"] = {stat: int(val) for stat, val in zip(stats, parts)}
    return "menunode_behavior"

def menunode_behavior(caller, raw_string="", **kwargs):
    text = "|wDescribe basic behavior or reactions:|n"
    options = {"key": "_default", "goto": _set_behavior}
    return text, options

def _set_behavior(caller, raw_string, **kwargs):
    caller.ndb.buildnpc["behavior"] = raw_string.strip()
    return "menunode_skills"

def menunode_skills(caller, raw_string="", **kwargs):
    text = "|wList any skills or attacks (comma separated):|n"
    options = {"key": "_default", "goto": _set_skills}
    return text, options

def _set_skills(caller, raw_string, **kwargs):
    skills = [s.strip() for s in raw_string.split(",") if s.strip()]
    caller.ndb.buildnpc["skills"] = skills
    return "menunode_ai"

def menunode_ai(caller, raw_string="", **kwargs):
    text = "|wAI type (e.g. passive, aggressive):|n"
    options = {"key": "_default", "goto": _set_ai}
    return text, options

def _set_ai(caller, raw_string, **kwargs):
    caller.ndb.buildnpc["ai_type"] = raw_string.strip()
    return "menunode_confirm"

def menunode_confirm(caller, raw_string="", **kwargs):
    data = caller.ndb.buildnpc
    if not isinstance(data, dict):
        caller.msg("Error: NPC data missing. Restarting builder.")
        return None
    text = "|wConfirm NPC Creation|n\n"
    for key, val in data.items():
        if key == "primary_stats":
            stats = " ".join(f"{s}:{v}" for s, v in val.items())
            text += f"{key}: {stats}\n"
        else:
            text += f"{key}: {val}\n"
    text += "\nCreate this NPC?"
    options = [
        {"desc": "Yes", "goto": (_create_npc, {"register": False})},
        {"desc": "Yes & Save Prototype", "goto": (_create_npc, {"register": True})},
        {"desc": "No", "goto": _cancel},
    ]
    return text, options

def _create_npc(caller, raw_string, register=False, **kwargs):
    data = caller.ndb.buildnpc
    if not isinstance(data, dict):
        caller.msg("Error: NPC data missing. Aborting.")
        return None
    npc = data.get("edit_obj") or create_object(NPC, key=data.get("key"), location=caller.location)
    npc.db.desc = data.get("desc")
    npc.tags.add("npc")
    if npc_type := data.get("npc_type"):
        npc.tags.add(npc_type, category="npc_type")
    if guild := data.get("guild_affiliation"):
        npc.tags.add(guild, category="guild_affiliation")
    npc.db.ai_type = data.get("ai_type")
    npc.db.behavior = data.get("behavior")
    npc.db.skills = data.get("skills")
    npc.db.creature_type = data.get("creature_type")
    npc.db.level = data.get("level", 1)
    for trait, val in {
        "health": data.get("hp"),
        "mana": data.get("mp"),
        "stamina": data.get("sp"),
    }.items():
        if val is not None and npc.traits.get(trait):
            npc.traits.get(trait).base = val
            npc.traits.get(trait).current = val
    if stats := data.get("primary_stats"):
        for key, val in stats.items():
            if npc.traits.get(key):
                npc.traits.get(key).base = val
        npc.db.base_primary_stats = stats
    slots = list(SLOT_ORDER)
    if data.get("creature_type") == "quadruped":
        for slot in ("twohanded", "mainhand", "offhand"):
            if slot in slots:
                slots.remove(slot)
    npc.db.equipment = {slot: None for slot in slots}
    if register:
        from world import prototypes

        proto = {k: v for k, v in data.items() if k != "edit_obj"}
        prototypes.register_npc_prototype(data.get("key"), proto)
        caller.msg(f"NPC {npc.key} created and prototype saved.")
    else:
        caller.msg(f"NPC {npc.key} created.")
    caller.ndb.buildnpc = None
    return None

def _cancel(caller, raw_string, **kwargs):
    caller.msg("NPC creation cancelled.")
    caller.ndb.buildnpc = None
    return None


class CmdCNPC(Command):
    """Create or edit an NPC using a guided menu."""

    key = "cnpc"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: cnpc start <key> | cnpc edit <npc>")
            return
        parts = self.args.split(None, 1)
        sub = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        if sub == "start":
            if not rest:
                self.msg("Usage: cnpc start <key>")
                return
            self.caller.ndb.buildnpc = {"key": rest.strip()}
            EvMenu(self.caller, "commands.npc_builder", startnode="menunode_desc")
            return
        if sub == "edit":
            if not rest:
                self.msg("Usage: cnpc edit <npc>")
                return
            npc = self.caller.search(rest, global_search=True)
            if not npc or not npc.is_typeclass(NPC, exact=False):
                self.msg("Invalid NPC.")
                return
            data = {
                "edit_obj": npc,
                "key": npc.key,
                "desc": npc.db.desc,
                "npc_type": npc.tags.get(category="npc_type") or "",
                "creature_type": npc.db.creature_type or "humanoid",
                "level": npc.db.level or 1,
                "hp": npc.traits.health.base if npc.traits.get("health") else 0,
                "mp": npc.traits.mana.base if npc.traits.get("mana") else 0,
                "sp": npc.traits.stamina.base if npc.traits.get("stamina") else 0,
                "primary_stats": npc.db.base_primary_stats or {},
                "behavior": npc.db.behavior or "",
                "skills": npc.db.skills or [],
                "ai_type": npc.db.ai_type or "",
            }
            self.caller.ndb.buildnpc = data
            EvMenu(self.caller, "commands.npc_builder", startnode="menunode_desc")
            return
        self.msg("Usage: cnpc start <key> | cnpc edit <npc>")

