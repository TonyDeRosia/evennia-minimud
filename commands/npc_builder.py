from evennia.utils.evmenu import EvMenu
from evennia.utils import make_iter
from evennia import create_object
from evennia.prototypes import spawner
from typeclasses.characters import NPC
from utils.slots import SLOT_ORDER
from .command import Command
import re

# NPC types that can be selected in the builder
ALLOWED_NPC_TYPES = (
    "merchant",
    "guard",
    "questgiver",
    "guildmaster",
    "banker",
    "guild_receptionist",
    "craftsman",
)


# Menu nodes for NPC creation

def menunode_desc(caller, raw_string="", **kwargs):
    """Prompt for a short description."""
    default = caller.ndb.buildnpc.get("desc", "")
    text = (
        "|wEnter a short description for the NPC|n "
        "(e.g. 'A grumpy orc')"
    )
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = {"key": "_default", "goto": _set_desc}
    return text, options

def _set_desc(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_desc"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("desc", "")
    caller.ndb.buildnpc["desc"] = string
    return "menunode_creature_type"

def menunode_npc_type(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("npc_type", "")
    types = "/".join(ALLOWED_NPC_TYPES)
    text = f"|wEnter NPC type ({types})|n"
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = {"key": "_default", "goto": _set_npc_type}
    return text, options

def _set_npc_type(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    if string == "back":
        if caller.ndb.buildnpc.get("creature_type") == "unique":
            return "menunode_custom_slots"
        return "menunode_creature_type"
    if not string or string == "skip":
        string = caller.ndb.buildnpc.get("npc_type", "").lower()
    if string and string not in ALLOWED_NPC_TYPES:
        caller.msg(f"Invalid NPC type. Choose from: {', '.join(ALLOWED_NPC_TYPES)}")
        return "menunode_npc_type"
    caller.ndb.buildnpc["npc_type"] = string
    if string == "guild_receptionist":
        return "menunode_guild_affiliation"
    return "menunode_level"

def menunode_guild_affiliation(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("guild_affiliation", "")
    text = "|wEnter guild tag for this receptionist|n"
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = {"key": "_default", "goto": _set_guild_affiliation}
    return text, options

def _set_guild_affiliation(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_npc_type"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("guild_affiliation", "")
    caller.ndb.buildnpc["guild_affiliation"] = string
    return "menunode_level"

def menunode_creature_type(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("creature_type", "humanoid")
    text = "|wCreature type (humanoid/quadruped/unique)|n"
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = {"key": "_default", "goto": _set_creature_type}
    return text, options

def _set_creature_type(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_desc"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("creature_type", "humanoid")
    ctype = string.lower() or "humanoid"
    caller.ndb.buildnpc["creature_type"] = ctype
    if ctype == "quadruped":
        caller.ndb.buildnpc["equipment_slots"] = ["head", "body", "front_legs", "hind_legs"]
        return "menunode_npc_type"
    if ctype == "unique":
        caller.ndb.buildnpc["equipment_slots"] = list(SLOT_ORDER)
        return "menunode_custom_slots"
    caller.ndb.buildnpc["equipment_slots"] = list(SLOT_ORDER)
    return "menunode_npc_type"

def menunode_custom_slots(caller, raw_string="", **kwargs):
    slots = caller.ndb.buildnpc.get("equipment_slots", list(SLOT_ORDER))
    text = "|wEdit Equipment Slots|n\n"
    text += ", ".join(slots) if slots else "None"
    text += ("\nCommands:\n"
             "  add <slot> - add a slot\n"
             "  remove <slot> - remove a slot\n"
             "  done - finish editing\n"
             "  back - previous step")
    options = {"key": "_default", "goto": _edit_custom_slots}
    return text, options

def _edit_custom_slots(caller, raw_string, **kwargs):
    string = raw_string.strip()
    slots = caller.ndb.buildnpc.setdefault("equipment_slots", list(SLOT_ORDER))
    if string.lower() == "back":
        return "menunode_creature_type"
    if string.lower() in ("done", "finish", "skip", ""):
        return "menunode_npc_type"
    if string.lower().startswith("add "):
        slot = string[4:].strip().lower()
        if slot and slot not in slots:
            slots.append(slot)
            caller.msg(f"Added {slot} slot.")
        else:
            caller.msg("Slot already present or invalid.")
        return "menunode_custom_slots"
    if string.lower().startswith("remove "):
        slot = string[7:].strip().lower()
        if slot in slots:
            slots.remove(slot)
            caller.msg(f"Removed {slot} slot.")
        else:
            caller.msg("Slot not found.")
        return "menunode_custom_slots"
    caller.msg("Unknown command.")
    return "menunode_custom_slots"

def menunode_level(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("level", 1)
    text = f"|wLevel of NPC (1-100)|n [default: {default}]\n(back to go back, skip for default)"
    options = {"key": "_default", "goto": _set_level}
    return text, options

def _set_level(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        if caller.ndb.buildnpc.get("npc_type") == "guild_receptionist":
            return "menunode_guild_affiliation"
        return "menunode_npc_type"
    if not string or string.lower() == "skip":
        caller.ndb.buildnpc["level"] = caller.ndb.buildnpc.get("level", 1)
        return "menunode_resources"
    try:
        val = int(string)
    except ValueError:
        caller.msg("Enter a number between 1 and 100.")
        return "menunode_level"
    if not 1 <= val <= 100:
        caller.msg("Enter a number between 1 and 100.")
        return "menunode_level"
    caller.ndb.buildnpc["level"] = val
    return "menunode_resources"

def menunode_resources(caller, raw_string="", **kwargs):
    hp = caller.ndb.buildnpc.get("hp", 0)
    mp = caller.ndb.buildnpc.get("mp", 0)
    sp = caller.ndb.buildnpc.get("sp", 0)
    default = f"{hp} {mp} {sp}"
    text = (
        f"|wEnter HP MP SP separated by spaces|n [default: {default}]\n"
        "(back to go back, skip for default)"
    )
    options = {"key": "_default", "goto": _set_resources}
    return text, options

def _set_resources(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_level"
    if not string or string.lower() == "skip":
        caller.ndb.buildnpc["hp"] = caller.ndb.buildnpc.get("hp", 0)
        caller.ndb.buildnpc["mp"] = caller.ndb.buildnpc.get("mp", 0)
        caller.ndb.buildnpc["sp"] = caller.ndb.buildnpc.get("sp", 0)
        return "menunode_stats"
    parts = string.split()
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        caller.msg("Enter three numbers separated by spaces.")
        return "menunode_resources"
    caller.ndb.buildnpc["hp"] = int(parts[0])
    caller.ndb.buildnpc["mp"] = int(parts[1])
    caller.ndb.buildnpc["sp"] = int(parts[2])
    return "menunode_stats"

def menunode_stats(caller, raw_string="", **kwargs):
    data = caller.ndb.buildnpc.get("primary_stats", {})
    stats_order = ["STR", "CON", "DEX", "INT", "WIS", "LUCK"]
    default = " ".join(str(data.get(stat, 0)) for stat in stats_order)
    text = (
        f"|wEnter STR CON DEX INT WIS LUCK separated by spaces|n [default: {default}]\n"
        "(back to go back, skip for default)"
    )
    options = {"key": "_default", "goto": _set_stats}
    return text, options

def _set_stats(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_resources"
    stats = ["STR", "CON", "DEX", "INT", "WIS", "LUCK"]
    if not string or string.lower() == "skip":
        caller.ndb.buildnpc["primary_stats"] = {
            stat: caller.ndb.buildnpc.get("primary_stats", {}).get(stat, 0)
            for stat in stats
        }
        return "menunode_behavior"
    parts = string.split()
    if len(parts) != 6 or not all(p.isdigit() for p in parts):
        caller.msg("Enter six numbers separated by spaces.")
        return "menunode_stats"
    caller.ndb.buildnpc["primary_stats"] = {
        stat: int(val) for stat, val in zip(stats, parts)
    }
    return "menunode_behavior"

def menunode_behavior(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("behavior", "")
    text = "|wDescribe basic behavior or reactions|n"
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = {"key": "_default", "goto": _set_behavior}
    return text, options

def _set_behavior(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_stats"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("behavior", "")
    caller.ndb.buildnpc["behavior"] = string
    return "menunode_skills"

def menunode_skills(caller, raw_string="", **kwargs):
    skills = caller.ndb.buildnpc.get("skills", [])
    default = ", ".join(skills)
    text = "|wList any skills or attacks (comma separated)|n"
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = {"key": "_default", "goto": _set_skills}
    return text, options

def _set_skills(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_behavior"
    if not string or string.lower() == "skip":
        skills = caller.ndb.buildnpc.get("skills", [])
    else:
        skills = [s.strip() for s in string.split(",") if s.strip()]
    caller.ndb.buildnpc["skills"] = skills
    return "menunode_ai"

def menunode_ai(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("ai_type", "")
    text = "|wAI type (e.g. passive, aggressive)|n"
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = {"key": "_default", "goto": _set_ai}
    return text, options

def _set_ai(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_skills"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("ai_type", "")
    caller.ndb.buildnpc["ai_type"] = string
    return "menunode_triggers"

def menunode_triggers(caller, raw_string="", **kwargs):
    """Main trigger menu."""
    text = "|wTrigger Menu|n"
    options = [
        {"desc": "Add trigger", "goto": "menunode_trigger_add"},
        {"desc": "Delete trigger", "goto": "menunode_trigger_delete"},
        {"desc": "List triggers", "goto": "menunode_trigger_list"},
        {"desc": "Finish", "goto": "menunode_confirm"},
    ]
    return text, options

def menunode_trigger_list(caller, raw_string="", **kwargs):
    """Show all triggers."""
    triggers = caller.ndb.buildnpc.get("triggers") or {}
    text = "|wCurrent Triggers|n\n"
    if triggers:
        for event, (match, reaction) in triggers.items():
            text += f"{event}: \"{match}\" -> {reaction}\n"
    else:
        text += "None\n"
    options = [{"desc": "Back", "goto": "menunode_triggers"}]
    return text, options

def menunode_trigger_add(caller, raw_string="", **kwargs):
    """Choose trigger event type."""
    text = "|wSelect event type|n"
    options = [
        {"desc": "on_enter", "goto": (_set_trigger_event, {"event": "on_enter"})},
        {"desc": "on_speak", "goto": (_set_trigger_event, {"event": "on_speak"})},
        {"desc": "on_attack", "goto": (_set_trigger_event, {"event": "on_attack"})},
        {"desc": "on_give_item", "goto": (_set_trigger_event, {"event": "on_give_item"})},
        {"desc": "on_timer", "goto": (_set_trigger_event, {"event": "on_timer"})},
        {"desc": "custom", "goto": "menunode_trigger_custom"},
        {"desc": "Back", "goto": "menunode_triggers"},
    ]
    return text, options

def menunode_trigger_custom(caller, raw_string="", **kwargs):
    """Prompt for custom event name."""
    text = "|wEnter custom event name|n"
    options = {"key": "_default", "goto": _set_custom_event}
    return text, options

def _set_custom_event(caller, raw_string, **kwargs):
    event = raw_string.strip()
    if not event:
        caller.msg("Enter a valid event name.")
        return "menunode_trigger_custom"
    return _set_trigger_event(caller, None, event=event)

def _set_trigger_event(caller, raw_string, event=None, **kwargs):
    caller.ndb.trigger_event = event
    return "menunode_trigger_match"

def menunode_trigger_match(caller, raw_string="", **kwargs):
    text = "|wEnter match text (blank for none)|n"
    options = {"key": "_default", "goto": _set_trigger_match}
    return text, options

def _set_trigger_match(caller, raw_string, **kwargs):
    caller.ndb.trigger_match = raw_string.strip()
    return "menunode_trigger_react"

def menunode_trigger_react(caller, raw_string="", **kwargs):
    text = "|wEnter reaction command|n"
    options = {"key": "_default", "goto": _save_trigger}
    return text, options

def _save_trigger(caller, raw_string, **kwargs):
    reaction = raw_string.strip()
    event = caller.ndb.trigger_event
    match = caller.ndb.trigger_match
    triggers = caller.ndb.buildnpc.setdefault("triggers", {})
    triggers[event] = (match, reaction)
    caller.ndb.trigger_event = None
    caller.ndb.trigger_match = None
    caller.msg("Trigger added.")
    return "menunode_triggers"

def menunode_trigger_delete(caller, raw_string="", **kwargs):
    """Select trigger to delete."""
    triggers = caller.ndb.buildnpc.get("triggers") or {}
    if not triggers:
        caller.msg("No triggers to delete.")
        return "menunode_triggers"
    text = "|wSelect trigger to delete|n"
    options = []
    for event, (match, reaction) in triggers.items():
        desc = f"{event}: \"{match}\" -> {reaction}"
        options.append({"desc": desc, "goto": (_del_trigger, {"event": event})})
    options.append({"desc": "Back", "goto": "menunode_triggers"})
    return text, options

def _del_trigger(caller, raw_string, event=None, **kwargs):
    triggers = caller.ndb.buildnpc.get("triggers") or {}
    if event in triggers:
        del triggers[event]
        caller.msg("Trigger removed.")
    return "menunode_triggers"


def menunode_confirm(caller, raw_string="", **kwargs):
    data = caller.ndb.buildnpc
    required = {"key"}
    if not isinstance(data, dict) or not required.issubset(data):
        caller.msg("Error: NPC data incomplete. Restarting builder.")
        return None
    text = "|wConfirm NPC Creation|n\n"
    for key, val in data.items():
        if key == "primary_stats":
            stats = " ".join(f"{s}:{v}" for s, v in val.items())
            text += f"{key}: {stats}\n"
        elif key == "triggers":
            if val:
                for event, (match, reaction) in val.items():
                    text += f"trigger {event}: \"{match}\" -> {reaction}\n"
            else:
                text += "triggers: None\n"
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
        npc.tags.add(npc_type, category="npc_role")
    if guild := data.get("guild_affiliation"):
        npc.tags.add(guild, category="guild_affiliation")
    npc.db.ai_type = data.get("ai_type")
    npc.db.behavior = data.get("behavior")
    npc.db.skills = data.get("skills")
    npc.db.triggers = data.get("triggers") or {}
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
    slots = list(data.get("equipment_slots") or [])
    if not slots:
        if data.get("creature_type") == "quadruped":
            slots = ["head", "body", "front_legs", "hind_legs"]
        else:
            slots = list(SLOT_ORDER)
    npc.db.equipment_slots = slots
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
            self.msg("Usage: cnpc start <key> | cnpc edit <npc> | cnpc dev_spawn <proto>")
            return
        parts = self.args.split(None, 1)
        sub = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        if sub == "start":
            if not rest:
                self.msg("Usage: cnpc start <key>")
                return
            self.caller.ndb.buildnpc = {"key": rest.strip(), "triggers": {}}
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
                "equipment_slots": npc.db.equipment_slots or list(SLOT_ORDER),
                "level": npc.db.level or 1,
                "hp": npc.traits.health.base if npc.traits.get("health") else 0,
                "mp": npc.traits.mana.base if npc.traits.get("mana") else 0,
                "sp": npc.traits.stamina.base if npc.traits.get("stamina") else 0,
                "primary_stats": npc.db.base_primary_stats or {},
                "behavior": npc.db.behavior or "",
                "skills": npc.db.skills or [],
                "ai_type": npc.db.ai_type or "",
                "triggers": npc.db.triggers or {},
            }
            self.caller.ndb.buildnpc = data
            EvMenu(self.caller, "commands.npc_builder", startnode="menunode_desc")
            return
        if sub == "dev_spawn":
            if not self.caller.check_permstring("Developer"):
                self.msg("Developer permission required.")
                return
            if not rest:
                self.msg("Usage: cnpc dev_spawn <proto>")
                return
            proto = rest
            try:
                obj = spawner.spawn(proto)[0]
            except KeyError:
                self.msg(f"Unknown prototype: {proto}")
                return
            obj.move_to(self.caller.location, quiet=True)
            self.msg(f"Spawned {obj.get_display_name(self.caller)}.")
            return
        self.msg("Usage: cnpc start <key> | cnpc edit <npc> | cnpc dev_spawn <proto>")

