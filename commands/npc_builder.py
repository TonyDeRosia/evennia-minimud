from evennia.utils.evmenu import EvMenu
from evennia.utils import make_iter, dedent
from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.prototypes import spawner
from utils.mob_proto import spawn_from_vnum
from evennia.prototypes.prototypes import PROTOTYPE_TAG_CATEGORY
from typeclasses.characters import NPC
from utils.slots import SLOT_ORDER
from utils.menu_utils import add_back_skip
from .command import Command
from django.conf import settings
import re
from world.mob_constants import (
    ACTFLAGS,
    AFFECTED_BY,
    LANGUAGES,
    BODYPARTS,
    RIS_TYPES,
    ATTACK_TYPES,
    DEFENSE_TYPES,
    parse_flag_list,
)


def validate_prototype(data: dict) -> list[str]:
    """Return a list of warnings for common prototype issues."""

    warnings: list[str] = []

    hp = data.get("hp")
    try:
        hp_val = int(hp) if hp is not None else None
    except (TypeError, ValueError):
        hp_val = None

    if not hp_val or hp_val <= 0:
        warnings.append("HP is set to zero.")

    actflags = {f.lower() for f in data.get("actflags", []) if isinstance(f, str)}
    ai_type = str(data.get("ai_type", "")).lower()

    if "aggressive" in actflags and "wimpy" in actflags:
        warnings.append("Aggressive and wimpy flags are both set.")

    if "sentinel" in actflags and ai_type == "wander":
        warnings.append("Sentinel flag conflicts with wander AI type.")

    return warnings

# NPC types that can be selected in the builder
ALLOWED_NPC_TYPES = (
    "merchant",
    "questgiver",
    "guildmaster",
    "banker",
    "guild_receptionist",
    "trainer",
    "guard",
    "wanderer",
)

# Mapping of simple keys to NPC typeclass paths
NPC_CLASS_MAP = {
    "base": "typeclasses.npcs.BaseNPC",
    "merchant": "typeclasses.npcs.merchant.MerchantNPC",
    "banker": "typeclasses.npcs.banker.BankerNPC",
    "trainer": "typeclasses.npcs.trainer.TrainerNPC",
    "wanderer": "typeclasses.npcs.wanderer.WandererNPC",
    "guildmaster": "typeclasses.npcs.guildmaster.GuildmasterNPC",
    "guild_receptionist": "typeclasses.npcs.guild_receptionist.GuildReceptionistNPC",
    "questgiver": "typeclasses.npcs.questgiver.QuestGiverNPC",
    "combat_trainer": "typeclasses.npcs.combat_trainer.CombatTrainerNPC",
    "event_npc": "typeclasses.npcs.event_npc.EventNPC",
}


# Additional configuration options
ALLOWED_ROLES = (
    "merchant",
    "banker",
    "trainer",
    "guildmaster",
    "guild_receptionist",
    "questgiver",
    "combat_trainer",
    "event_npc",
)

ALLOWED_AI_TYPES = (
    "passive",
    "aggressive",
    "defensive",
    "wander",
    "scripted",
)


# Menu nodes for NPC creation

def menunode_key(caller, raw_string="", **kwargs):
    """Prompt for the NPC key."""
    default = caller.ndb.buildnpc.get("key", "")
    text = "|wEnter NPC key|n"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wmerchant_01|n"
    options = add_back_skip({"key": "_default", "goto": _set_key}, _set_key)
    return text, options


def _set_key(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if not val or val.lower() == "skip":
        val = caller.ndb.buildnpc.get("key", "")
    if not val:
        caller.msg("Key is required.")
        return "menunode_key"
    caller.ndb.buildnpc = caller.ndb.buildnpc or {}
    caller.ndb.buildnpc["key"] = val
    return "menunode_desc"


def menunode_desc(caller, raw_string="", **kwargs):
    """Prompt for a short description."""
    default = caller.ndb.buildnpc.get("desc", "")
    text = (
        "|wEnter a short description for the NPC|n "
        "(e.g. 'A grumpy orc')\n"
        "Type |wback|n to edit the key or |wskip|n to keep the current value."
    )
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_desc}, _set_desc)
    return text, options

def _set_desc(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_key"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("desc", "")
    caller.ndb.buildnpc["desc"] = string
    return "menunode_creature_type"

def menunode_npc_type(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("npc_type", "")
    types = "/".join(ALLOWED_NPC_TYPES)
    text = dedent(
        f"""
        |wEnter NPC type|n ({types})
        Example: |wmerchant|n
        Type |wback|n to return or |wskip|n to keep the default.
        """
    )
    if default:
        text += f" [default: {default}]"
    options = add_back_skip({"key": "_default", "goto": _set_npc_type}, _set_npc_type)
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
    return "menunode_npc_class"

def menunode_guild_affiliation(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("guild_affiliation", "")
    text = "|wEnter guild tag for this receptionist|n"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wthieves_guild|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_guild_affiliation}, _set_guild_affiliation)
    return text, options

def _set_guild_affiliation(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_roles"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("guild_affiliation", "")
    caller.ndb.buildnpc["guild_affiliation"] = string
    return "menunode_role_details"

def menunode_creature_type(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("creature_type", "humanoid")
    text = dedent(
        """
        |wCreature type|n (humanoid/quadruped/unique)
        Example: |wquadruped|n
        Type |wback|n to return or |wskip|n to keep the default.
        """
    )
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"  # keep existing note for clarity
    options = add_back_skip({"key": "_default", "goto": _set_creature_type}, _set_creature_type)
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
             "  back - previous step\n"
             "Example: |wadd tail|n")
    options = add_back_skip({"key": "_default", "goto": _edit_custom_slots}, _edit_custom_slots)
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

def menunode_npc_class(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("npc_class", "base")
    classes = "/".join(NPC_CLASS_MAP)
    text = f"|wChoose NPC class ({classes})|n"
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_npc_class}, _set_npc_class)
    return text, options

def _set_npc_class(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    if string == "back":
        return "menunode_npc_type"
    if not string or string == "skip":
        string = caller.ndb.buildnpc.get("npc_class", "base")
    if string not in NPC_CLASS_MAP:
        caller.msg(f"Invalid class. Choose from: {', '.join(NPC_CLASS_MAP)}")
        return "menunode_npc_class"
    caller.ndb.buildnpc["npc_class"] = string

    return "menunode_roles"

def menunode_roles(caller, raw_string="", **kwargs):
    roles = caller.ndb.buildnpc.get("roles", [])
    available = ", ".join(ALLOWED_ROLES)
    text = "|wEdit NPC Roles|n\n"
    text += ", ".join(roles) if roles else "None"
    text += (
        f"\nAvailable roles: {available}\n"
        "Commands:\n  add <role>\n  remove <role>\n  done - finish\n  back - previous step\n"
        "Example: |wadd merchant|n"
    )
    options = add_back_skip({"key": "_default", "goto": _edit_roles}, _edit_roles)
    return text, options

def _edit_roles(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    roles = caller.ndb.buildnpc.setdefault("roles", [])
    if string == "back":
        return "menunode_npc_class"
    if string in ("done", "finish", "skip", ""):
        return "menunode_role_details"
    if string.startswith("add "):
        role = string[4:].strip()
        if role in ALLOWED_ROLES and role not in roles:
            roles.append(role)
            caller.msg(f"Added role {role}.")
        else:
            caller.msg("Invalid or duplicate role.")
        return "menunode_roles"
    if string.startswith("remove "):
        role = string[7:].strip()
        if role in roles:
            roles.remove(role)
            caller.msg(f"Removed role {role}.")
        else:
            caller.msg("Role not found.")
        return "menunode_roles"
    caller.msg("Unknown command.")
    return "menunode_roles"

def menunode_role_details(caller, raw_string="", **kwargs):
    roles = caller.ndb.buildnpc.get("roles", [])
    if "merchant" in roles and "merchant_markup" not in caller.ndb.buildnpc:
        return "menunode_merchant_pricing"
    if any(r in roles for r in ("guildmaster", "guild_receptionist")) and not caller.ndb.buildnpc.get("guild_affiliation"):
        return "menunode_guild_affiliation"
    return "menunode_level"

def menunode_merchant_pricing(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("merchant_markup", 1.0)
    text = dedent(
        f"""
        |wMerchant price multiplier|n [default: {default}]
        Example: |w1.5|n
        (back to go back, skip for default)
        """
    )
    options = add_back_skip({"key": "_default", "goto": _set_merchant_pricing}, _set_merchant_pricing)
    return text, options

def _set_merchant_pricing(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_roles"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("merchant_markup", 1.0)
    else:
        try:
            val = float(string)
        except ValueError:
            caller.msg("Enter a number.")
            return "menunode_merchant_pricing"
    caller.ndb.buildnpc["merchant_markup"] = val
    return "menunode_role_details"

def menunode_level(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("level", 1)
    text = dedent(
        f"""
        |wLevel of NPC (1-100)|n [default: {default}]
        Example: |w10|n
        (back to go back, skip for default)
        """
    )
    options = add_back_skip({"key": "_default", "goto": _set_level}, _set_level)
    return text, options

def _set_level(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_roles"
    if not string or string.lower() == "skip":
        caller.ndb.buildnpc["level"] = caller.ndb.buildnpc.get("level", 1)
        return "menunode_exp_reward"
    try:
        val = int(string)
    except ValueError:
        caller.msg("Enter a number between 1 and 100.")
        return "menunode_level"
    if not 1 <= val <= 100:
        caller.msg("Enter a number between 1 and 100.")
        return "menunode_level"
    caller.ndb.buildnpc["level"] = val
    return "menunode_exp_reward"

def menunode_exp_reward(caller, raw_string="", **kwargs):
    """Prompt for experience reward given when this NPC is defeated."""
    level = caller.ndb.buildnpc.get("level", 1)
    default = caller.ndb.buildnpc.get(
        "exp_reward", level * settings.DEFAULT_XP_PER_LEVEL
    )
    text = dedent(
        f"""
        |wEXP reward|n [default: {default}]
        Example: |w{level * settings.DEFAULT_XP_PER_LEVEL}|n
        (back to go back, skip for default)
        """
    )
    options = add_back_skip({"key": "_default", "goto": _set_exp_reward}, _set_exp_reward)
    return text, options


def _set_exp_reward(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_level"
    if not string or string.lower() == "skip":
        level = caller.ndb.buildnpc.get("level", 1)
        val = caller.ndb.buildnpc.get(
            "exp_reward", level * settings.DEFAULT_XP_PER_LEVEL
        )
    else:
        try:
            val = int(string)
        except ValueError:
            caller.msg("Enter a number.")
            return "menunode_exp_reward"
    caller.ndb.buildnpc["exp_reward"] = val
    return "menunode_resources"

def menunode_resources(caller, raw_string="", **kwargs):
    hp = caller.ndb.buildnpc.get("hp", 0)
    mp = caller.ndb.buildnpc.get("mp", 0)
    sp = caller.ndb.buildnpc.get("sp", 0)
    default = f"{hp} {mp} {sp}"
    text = dedent(
        f"""
        |wEnter HP MP SP separated by spaces|n [default: {default}]
        Example: |w100 50 30|n
        (back to go back, skip for default)
        """
    )
    options = add_back_skip({"key": "_default", "goto": _set_resources}, _set_resources)
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
    text = dedent(
        f"""
        |wEnter STR CON DEX INT WIS LUCK separated by spaces|n [default: {default}]
        Example: |w10 10 10 10 10 10|n
        (back to go back, skip for default)
        """
    )
    options = add_back_skip({"key": "_default", "goto": _set_stats}, _set_stats)
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
    text += "\nExample: |wSells potions and greets players|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_behavior}, _set_behavior)
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
    text += "\nExample: |wfireball, slash, heal|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_skills}, _set_skills)
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
    return "menunode_spells"


def menunode_spells(caller, raw_string="", **kwargs):
    spells = caller.ndb.buildnpc.get("spells", [])
    default = ", ".join(spells)
    text = "|wList any spells (comma separated)|n"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wfireball, heal|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_spells}, _set_spells)
    return text, options


def _set_spells(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_skills"
    if not string or string.lower() == "skip":
        spells = caller.ndb.buildnpc.get("spells", [])
    else:
        spells = [s.strip() for s in string.split(",") if s.strip()]
    caller.ndb.buildnpc["spells"] = spells
    return "menunode_ai"

def menunode_ai(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("ai_type", "")
    types = "/".join(ALLOWED_AI_TYPES)
    text = dedent(
        f"""
        |wAI type|n ({types})
        Example: |waggressive|n
        (back to go back, skip for default)
        """
    )
    if default:
        text += f" [default: {default}]"
    options = add_back_skip({"key": "_default", "goto": _set_ai}, _set_ai)
    return text, options

def _set_ai(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_skills"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("ai_type", "")
    if string and string not in ALLOWED_AI_TYPES:
        caller.msg(f"Invalid AI type. Choose from: {', '.join(ALLOWED_AI_TYPES)}")
        return "menunode_ai"
    caller.ndb.buildnpc["ai_type"] = string
    if caller.ndb.buildnpc.get("use_mob"):
        return "menunode_actflags"
    return "menunode_triggers"


def menunode_actflags(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("actflags", [])
    flags = ", ".join(a.value for a in ACTFLAGS)
    text = "|wAct Flags|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += f"\nAvailable: {flags}"
    text += "\nExample: |wsentinel aggressive assist call_for_help|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_actflags}, _set_actflags)
    return text, options


def _set_actflags(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_ai"
    if not string or string.lower() == "skip":
        flags = caller.ndb.buildnpc.get("actflags", [])
    else:
        try:
            flags = [f.value for f in parse_flag_list(string, ACTFLAGS)]
        except Exception:
            caller.msg("Invalid flag.")
            return "menunode_actflags"
    caller.ndb.buildnpc["actflags"] = flags
    return "menunode_affects"


def menunode_affects(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("affected_by", [])
    choices = ", ".join(a.value for a in AFFECTED_BY)
    text = "|wAffects|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += f"\nAvailable: {choices}"
    text += "\nExample: |winvisible detect_magic|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_affects}, _set_affects)
    return text, options


def _set_affects(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_actflags"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("affected_by", [])
    else:
        try:
            val = [f.value for f in parse_flag_list(string, AFFECTED_BY)]
        except Exception:
            caller.msg("Invalid affect.")
            return "menunode_affects"
    caller.ndb.buildnpc["affected_by"] = val
    return "menunode_resists"


def menunode_resists(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("ris", [])
    choices = ", ".join(r.value for r in RIS_TYPES)
    text = "|wResistances|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += f"\nAvailable: {choices}"
    text += "\nExample: |wfire cold energy|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_resists}, _set_resists)
    return text, options


def _set_resists(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_affects"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("ris", [])
    else:
        try:
            val = [f.value for f in parse_flag_list(string, RIS_TYPES)]
        except Exception:
            caller.msg("Invalid type.")
            return "menunode_resists"
    caller.ndb.buildnpc["ris"] = val
    return "menunode_bodyparts"


def menunode_bodyparts(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("bodyparts", [])
    parts = ", ".join(b.value for b in BODYPARTS)
    text = "|wBodyparts|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += f"\nAvailable: {parts}"
    text += "\nExample: |whead arms legs|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_bodyparts}, _set_bodyparts)
    return text, options


def _set_bodyparts(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_resists"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("bodyparts", [])
    else:
        try:
            val = [f.value for f in parse_flag_list(string, BODYPARTS)]
        except Exception:
            caller.msg("Invalid bodypart.")
            return "menunode_bodyparts"
    caller.ndb.buildnpc["bodyparts"] = val
    return "menunode_attack"


def menunode_attack(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("attack_types", [])
    choices = ", ".join(a.value for a in ATTACK_TYPES)
    text = "|wAttack types|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += f"\nAvailable: {choices}"
    text += "\nExample: |wbite claw|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_attack}, _set_attack)
    return text, options


def _set_attack(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_bodyparts"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("attack_types", [])
    else:
        try:
            val = [f.value for f in parse_flag_list(string, ATTACK_TYPES)]
        except Exception:
            caller.msg("Invalid attack type.")
            return "menunode_attack"
    caller.ndb.buildnpc["attack_types"] = val
    return "menunode_defense"


def menunode_defense(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("defense_types", [])
    choices = ", ".join(d.value for d in DEFENSE_TYPES)
    text = "|wDefense types|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += f"\nAvailable: {choices}"
    text += "\nExample: |wparry dodge|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_defense}, _set_defense)
    return text, options


def _set_defense(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_attack"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("defense_types", [])
    else:
        try:
            val = [f.value for f in parse_flag_list(string, DEFENSE_TYPES)]
        except Exception:
            caller.msg("Invalid defense type.")
            return "menunode_defense"
    caller.ndb.buildnpc["defense_types"] = val
    return "menunode_languages"


def menunode_languages(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("languages", [])
    choices = ", ".join(l.value for l in LANGUAGES)
    text = "|wLanguages|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += f"\nAvailable: {choices}"
    text += "\nExample: |wcommon elvish|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_languages}, _set_languages)
    return text, options


def _set_languages(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_defense"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("languages", [])
    else:
        try:
            val = [f.value for f in parse_flag_list(string, LANGUAGES)]
        except Exception:
            caller.msg("Invalid language.")
            return "menunode_languages"
    caller.ndb.buildnpc["languages"] = val
    return "menunode_script"

def menunode_script(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("script", "")
    text = "|wScript to attach to NPC (e.g. bandit_ai.BanditAI)|n"
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_script}, _set_script)
    return text, options


def _set_script(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_languages"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("script", "")
    else:
        val = string
    caller.ndb.buildnpc["script"] = val
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
        for event, triglist in triggers.items():
            for trig in make_iter(triglist):
                if not isinstance(trig, dict):
                    continue
                match = trig.get("match", "")
                resp = trig.get("responses", trig.get("response", trig.get("reactions")))
                if isinstance(resp, list):
                    resp = ", ".join(resp)
                text += f"{event}: \"{match}\" -> {resp}\n"
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
        {"desc": "on_look", "goto": (_set_trigger_event, {"event": "on_look"})},
        {"desc": "on_timer", "goto": (_set_trigger_event, {"event": "on_timer"})},
        {"desc": "custom", "goto": "menunode_trigger_custom"},
        {"desc": "Back", "goto": "menunode_triggers"},
    ]
    return text, options

def menunode_trigger_custom(caller, raw_string="", **kwargs):
    """Prompt for custom event name."""
    text = "|wEnter custom event name|n"
    options = add_back_skip({"key": "_default", "goto": _set_custom_event}, _set_custom_event)
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
    options = add_back_skip({"key": "_default", "goto": _set_trigger_match}, _set_trigger_match)
    return text, options

def _set_trigger_match(caller, raw_string, **kwargs):
    caller.ndb.trigger_match = raw_string.strip()
    return "menunode_trigger_react"

def menunode_trigger_react(caller, raw_string="", **kwargs):
    text = "|wEnter reaction command(s) (comma or semicolon separated)|n"
    options = add_back_skip({"key": "_default", "goto": _save_trigger}, _save_trigger)
    return text, options

def _save_trigger(caller, raw_string, **kwargs):
    reaction = raw_string.strip()
    event = caller.ndb.trigger_event
    match = caller.ndb.trigger_match
    triggers = caller.ndb.buildnpc.setdefault("triggers", {})
    triglist = triggers.setdefault(event, [])

    responses = [part.strip() for part in re.split(r"[;,]", reaction) if part.strip()]
    triglist.append({"match": match, "responses": responses})
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
    for event, triglist in triggers.items():
        for idx, trig in enumerate(make_iter(triglist)):
            if not isinstance(trig, dict):
                continue
            match = trig.get("match", "")
            resp = trig.get("responses", trig.get("response", trig.get("reactions")))
            if isinstance(resp, list):
                resp = ", ".join(resp)
            desc = f"{event}: \"{match}\" -> {resp}"
            options.append(
                {"desc": desc, "goto": (_del_trigger, {"event": event, "index": idx})}
            )
    options.append({"desc": "Back", "goto": "menunode_triggers"})
    return text, options

def _del_trigger(caller, raw_string, event=None, index=None, **kwargs):
    triggers = caller.ndb.buildnpc.get("triggers") or {}
    triglist = triggers.get(event)
    if triglist and index is not None and 0 <= index < len(triglist):
        triglist.pop(index)
        if not triglist:
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
                for event, triglist in val.items():
                    for trig in make_iter(triglist):
                        if not isinstance(trig, dict):
                            continue
                        match = trig.get("match", "")
                        resp = trig.get("responses", trig.get("response", trig.get("reactions")))
                        if isinstance(resp, list):
                            resp = ", ".join(resp)
                        text += f"trigger {event}: \"{match}\" -> {resp}\n"
            else:
                text += "triggers: None\n"
        else:
            text += f"{key}: {val}\n"
    warnings = validate_prototype(data)
    if warnings:
        text += "|yWarnings:|n\n"
        for warn in warnings:
            text += f" - {warn}\n"
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
    tclass_path = NPC_CLASS_MAP.get(data.get("npc_class", "base"), "typeclasses.npcs.BaseNPC")
    if data.get("edit_obj"):
        npc = data.get("edit_obj")
        if npc.typeclass_path != tclass_path:
            npc.swap_typeclass(tclass_path, clean_attributes=False)
    else:
        npc = create_object(tclass_path, key=data.get("key"), location=caller.location)
    npc.db.desc = data.get("desc")
    npc.tags.add("npc")
    if npc_type := data.get("npc_type"):
        npc.tags.add(npc_type, category="npc_type")
        npc.tags.add(npc_type, category="npc_role")
    for role in data.get("roles", []):
        if role and not npc.tags.has(role, category="npc_role"):
            npc.tags.add(role, category="npc_role")
    if guild := data.get("guild_affiliation"):
        npc.tags.add(guild, category="guild_affiliation")
    if markup := data.get("merchant_markup"):
        npc.db.merchant_markup = markup
    npc.db.ai_type = data.get("ai_type")
    npc.db.behavior = data.get("behavior")
    npc.db.skills = data.get("skills")
    npc.db.spells = data.get("spells")
    npc.db.actflags = data.get("actflags")
    npc.db.affected_by = data.get("affected_by")
    npc.db.ris = data.get("ris")
    npc.db.bodyparts = data.get("bodyparts")
    npc.db.attack_types = data.get("attack_types")
    npc.db.defense_types = data.get("defense_types")
    npc.db.languages = data.get("languages")
    npc.db.triggers = data.get("triggers") or {}
    npc.db.exp_reward = data.get("exp_reward", 0)
    if script_path := data.get("script"):
        try:
            module, cls = script_path.rsplit(".", 1)
            mod = __import__(module, fromlist=[cls])
            script_cls = getattr(mod, cls)
            npc.scripts.add(script_cls, key=cls)
        except Exception as err:  # pragma: no cover - log errors
            caller.msg(f"Could not attach script {script_path}: {err}")
    npc.db.creature_type = data.get("creature_type")
    if data.get("use_mob"):
        npc.db.can_attack = True
        if not npc.db.natural_weapon:
            npc.db.natural_weapon = {
                "name": "fists",
                "damage_type": "bash",
                "damage": 1,
                "speed": 10,
                "stamina_cost": 5,
            }
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

        proto_key = data.get("proto_key", data.get("key"))
        # automatically prefix mob prototypes when using mobbuilder
        if data.get("use_mob") and not proto_key.startswith("mob_"):
            proto_key = f"mob_{proto_key}"
            data["proto_key"] = proto_key
        proto = {k: v for k, v in data.items() if k not in ("edit_obj", "proto_key")}
        proto["typeclass"] = tclass_path
        proto["exp_reward"] = data.get("exp_reward", 0)
        if data.get("use_mob"):
            proto["can_attack"] = True
            proto.setdefault(
                "natural_weapon",
                {
                    "name": "fists",
                    "damage_type": "bash",
                    "damage": 1,
                    "speed": 10,
                    "stamina_cost": 5,
                },
            )
        if data.get("script"):
            proto["scripts"] = [data["script"]]
        prototypes.register_npc_prototype(proto_key, proto)
        caller.msg(f"NPC {npc.key} created and prototype saved.")
    else:
        caller.msg(f"NPC {npc.key} created.")
    caller.ndb.buildnpc = None
    return None

def _cancel(caller, raw_string, **kwargs):
    caller.msg("NPC creation cancelled.")
    caller.ndb.buildnpc = None
    return None


def _gather_npc_data(npc):
    """Return a dict of editable NPC attributes."""
    return {
        "edit_obj": npc,
        "proto_key": npc.tags.get(category=PROTOTYPE_TAG_CATEGORY),
        "key": npc.key,
        "desc": npc.db.desc,
        "npc_type": npc.tags.get(category="npc_type") or "",
        "roles": [t for t in npc.tags.get(category="npc_role", return_list=True) or [] if t != npc.tags.get(category="npc_type")],
        "npc_class": next(
            (k for k, path in NPC_CLASS_MAP.items() if path == npc.typeclass_path),
            "base",
        ),
        "creature_type": npc.db.creature_type or "humanoid",
        "equipment_slots": npc.db.equipment_slots or list(SLOT_ORDER),
        "level": npc.db.level or 1,
        "hp": npc.traits.health.base if npc.traits.get("health") else 0,
        "mp": npc.traits.mana.base if npc.traits.get("mana") else 0,
        "sp": npc.traits.stamina.base if npc.traits.get("stamina") else 0,
        "primary_stats": npc.db.base_primary_stats or {},
        "behavior": npc.db.behavior or "",
        "skills": npc.db.skills or [],
        "spells": npc.db.spells or [],
        "ai_type": npc.db.ai_type or "",
        "actflags": npc.db.actflags or [],
        "affected_by": npc.db.affected_by or [],
        "ris": npc.db.ris or [],
        "bodyparts": npc.db.bodyparts or [],
        "attack_types": npc.db.attack_types or [],
        "defense_types": npc.db.defense_types or [],
        "languages": npc.db.languages or [],
        "exp_reward": npc.db.exp_reward or 0,
        "merchant_markup": npc.db.merchant_markup or 1.0,
        "guild_affiliation": npc.tags.get(category="guild_affiliation") or "",
        "triggers": npc.db.triggers or {},
        "script": next((scr.typeclass_path for scr in npc.scripts.all() if scr.key != "npc_ai"), ""),
    }


class CmdCNPC(Command):
    """Create or edit an NPC using a guided menu."""

    key = "cnpc"
    aliases = ["createnpc"]
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
            self.caller.ndb.buildnpc = {
                "key": rest.strip(),
                "triggers": {},
                "npc_class": "base",
                "roles": [],
                "skills": [],
                "spells": [],
                "ris": [],
                "exp_reward": 0,
                "merchant_markup": 1.0,
                "script": "",
            }
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
            data = _gather_npc_data(npc)
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
            from world import prototypes

            proto_dict = prototypes.get_npc_prototypes().get(proto)
            try:
                if proto_dict:
                    obj = spawner.spawn(proto_dict)[0]
                else:
                    obj = spawner.spawn(proto)[0]
            except KeyError:
                self.msg(f"Unknown prototype: {proto}")
                return
            obj.move_to(self.caller.location, quiet=True)
            self.msg(f"Spawned {obj.get_display_name(self.caller)}.")
            return
        self.msg("Usage: cnpc start <key> | cnpc edit <npc> | cnpc dev_spawn <proto>")


class CmdEditNPC(Command):
    """Open the NPC builder to edit an existing NPC."""

    key = "@editnpc"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @editnpc <npc>")
            return
        npc = self.caller.search(self.args.strip(), global_search=True)
        if not npc or not npc.is_typeclass(NPC, exact=False):
            self.msg("Invalid NPC.")
            return
        self.caller.ndb.buildnpc = _gather_npc_data(npc)
        EvMenu(self.caller, "commands.npc_builder", startnode="menunode_desc")


class CmdDeleteNPC(Command):
    """Delete an NPC after confirmation."""

    key = "@deletenpc"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @deletenpc <npc>")
            return
        npc = self.caller.search(self.args.strip(), global_search=True)
        if not npc or not npc.is_typeclass(NPC, exact=False):
            self.msg("Invalid NPC.")
            return
        confirm = yield (f"Delete {npc.key}? Yes/No")
        if confirm.strip().lower() not in ("yes", "y"):
            self.msg("Deletion cancelled.")
            return
        npc.delete()
        self.msg(f"{npc.key} deleted.")


class CmdCloneNPC(Command):
    """Create a copy of an NPC."""

    key = "@clonenpc"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def parse(self):
        self.source, _, self.newname = self.args.partition("=")
        self.source = self.source.strip()
        self.newname = self.newname.strip() if self.newname else ""

    def func(self):
        if not self.source:
            self.msg("Usage: @clonenpc <npc> [= <new_name>]")
            return
        npc = self.caller.search(self.source, global_search=True)
        if not npc or not npc.is_typeclass(NPC, exact=False):
            self.msg("Invalid NPC.")
            return
        new_key = self.newname or f"{npc.key}_copy"
        clone = ObjectDB.objects.copy_object(
            npc, new_key=new_key, new_location=self.caller.location
        )
        if clone:
            self.msg(f"Cloned {npc.key} to {clone.key}.")
        else:
            self.msg("Error cloning NPC.")


class CmdSpawnNPC(Command):
    """Spawn an NPC from a saved prototype."""

    key = "@spawnnpc"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @spawnnpc <prototype> or @spawnnpc <area>/<proto>")
            return
        arg = self.args.strip()
        from world import prototypes
        proto = None
        if arg.isdigit():
            obj = spawn_from_vnum(int(arg), location=self.caller.location)
            if not obj:
                self.msg("Unknown NPC prototype.")
                return
            key = None
        else:
            if "/" in arg:
                area, key = arg.split("/", 1)
                from world import area_npcs

                if key not in area_npcs.get_area_npc_list(area):
                    self.msg("Prototype not in that area's list.")
                    return
                proto = prototypes.get_npc_prototypes().get(key)
            else:
                key = arg
                proto = prototypes.get_npc_prototypes().get(arg)
            if not proto:
                self.msg("Unknown NPC prototype.")
                return
            tclass_path = NPC_CLASS_MAP.get(
                proto.get("npc_class", "base"), "typeclasses.npcs.BaseNPC"
            )
            proto = dict(proto)
            proto.setdefault("typeclass", tclass_path)
            obj = spawner.spawn(proto)[0]
            obj.move_to(self.caller.location, quiet=True)
            obj.db.prototype_key = key
        obj.db.area_tag = self.caller.location.db.area
        obj.db.spawn_room = self.caller.location
        self.msg(f"Spawned {obj.get_display_name(self.caller)}.")


class CmdListNPCs(Command):
    """List NPC prototypes available for an area."""

    key = "@listnpcs"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @listnpcs <area>")
            return
        area = self.args.strip()
        from world import area_npcs, prototypes

        keys = area_npcs.get_area_npc_list(area)
        if not keys:
            self.msg("No prototypes registered for that area.")
            return
        registry = prototypes.get_npc_prototypes()
        lines = []
        for key in keys:
            desc = registry.get(key, {}).get("desc", "")
            lines.append(f"{key} - {desc}" if desc else key)
        self.msg("\n".join(lines))


class CmdDupNPC(Command):
    """Duplicate an NPC prototype from an area's list."""

    key = "@dupnpc"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def parse(self):
        path, _, newname = self.args.partition("=")
        self.path = path.strip()
        self.newname = newname.strip() if newname else ""

    def func(self):
        if not self.path or "/" not in self.path:
            self.msg("Usage: @dupnpc <area>/<proto> [= <new_name>]")
            return
        area, key = self.path.split("/", 1)
        from world import area_npcs, prototypes

        if key not in area_npcs.get_area_npc_list(area):
            self.msg("Prototype not in that area's list.")
            return
        registry = prototypes.get_npc_prototypes()
        proto = registry.get(key)
        if not proto:
            self.msg("Unknown NPC prototype.")
            return
        new_key = self.newname or f"{key}_copy"
        if new_key in registry:
            self.msg("Prototype with that key already exists.")
            return
        new_proto = dict(proto)
        new_proto["key"] = new_key
        prototypes.register_npc_prototype(new_key, new_proto)
        area_npcs.add_area_npc(area, new_key)
        self.msg(f"Prototype {key} duplicated to {new_key} in area {area}.")

