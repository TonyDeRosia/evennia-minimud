from evennia.utils.evmenu import EvMenu
from evennia.utils import make_iter, dedent
from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.prototypes import spawner
from utils.mob_proto import spawn_from_vnum
from evennia.prototypes.prototypes import PROTOTYPE_TAG_CATEGORY
from typeclasses.characters import NPC
from utils.slots import SLOT_ORDER
from utils.menu_utils import add_back_skip, add_back_next, add_back_only
from world.scripts import classes
from utils import vnum_registry
from utils.mob_utils import calculate_combat_stats, mobprogs_to_triggers
from .command import Command
from django.conf import settings
from importlib import import_module
from evennia.utils import logger
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
from combat.combat_skills import SKILL_CLASSES


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


def _auto_fill_combat_stats(data: dict) -> None:
    """Populate missing combat stats if class and level are set."""
    combat_class = data.get("combat_class")
    level = data.get("level")
    if not combat_class or not level:
        return
    stats = calculate_combat_stats(combat_class, level)
    for field in ("hp", "mp", "sp", "armor", "initiative"):
        data.setdefault(field, stats[field])


# Primary roles that can be selected in the builder
ALLOWED_ROLES_PRIMARY = (
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


# Suggested skill lists for each NPC class
DEFAULT_SKILLS = list(SKILL_CLASSES.keys())
SKILLS_BY_CLASS = {
    "merchant": ["appraise"],
    "combat_trainer": DEFAULT_SKILLS,
    "base": DEFAULT_SKILLS,
}


def get_skills_for_class(npc_class: str) -> list[str]:
    """Return list of suggested skills for ``npc_class``."""
    return SKILLS_BY_CLASS.get(npc_class, DEFAULT_SKILLS)


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

# Modules allowed when importing scripted AI callbacks or Scripts
ALLOWED_SCRIPT_MODULES = ("scripts",)


def _import_script(path: str):
    """Safely import a script or callable from an allowed module."""
    module, attr = path.rsplit(".", 1)
    if not any(
        module == allowed or module.startswith(f"{allowed}.")
        for allowed in ALLOWED_SCRIPT_MODULES
    ):
        raise ImportError(f"Module '{module}' is not allowed")
    mod = import_module(module)
    return getattr(mod, attr)


def format_mob_summary(data: dict) -> str:
    """Return a formatted summary of NPC prototype data."""

    from evennia.utils.evtable import EvTable

    def fmt(value):
        if not value:
            return "--"
        if isinstance(value, dict):
            return ", ".join(f"{k}:{v}" for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value)
        return str(value)

    lines = [f"|cMob Prototype:|n {data.get('key', '--')}"]

    basic = EvTable(border="cells")
    basic.add_row("|cShort Desc|n", fmt(data.get("desc")))
    basic.add_row("|cLevel|n", fmt(data.get("level")))
    if "vnum" in data:
        basic.add_row("|cVNUM|n", fmt(data.get("vnum")))
    basic.add_row("|cClass|n", fmt(data.get("npc_class")))
    if data.get("combat_class"):
        basic.add_row("|cCombat Class|n", fmt(data.get("combat_class")))
    if data.get("race"):
        basic.add_row("|cRace|n", fmt(data.get("race")))
    if data.get("sex"):
        basic.add_row("|cSex|n", fmt(data.get("sex")))
    if data.get("weight"):
        basic.add_row("|cWeight|n", fmt(data.get("weight")))
    if data.get("role"):
        basic.add_row("|cRole|n", fmt(data.get("role")))
    if data.get("roles"):
        basic.add_row("|cExtra Roles|n", fmt(data.get("roles")))
    if data.get("creature_type"):
        basic.add_row("|cCreature|n", fmt(data.get("creature_type")))
    if data.get("guild_affiliation"):
        basic.add_row("|cGuild|n", fmt(data.get("guild_affiliation")))
    lines.append("\n|cBasic Info|n")
    lines.append(str(basic))

    stats = EvTable(border="cells")
    stats.add_row("|cHP|n", fmt(data.get("hp")))
    stats.add_row("|cMP|n", fmt(data.get("mp")))
    stats.add_row("|cSP|n", fmt(data.get("sp")))
    if data.get("damage") is not None:
        stats.add_row("|cDamage|n", fmt(data.get("damage")))
    if data.get("armor") is not None:
        stats.add_row("|cArmor|n", fmt(data.get("armor")))
    if data.get("initiative") is not None:
        stats.add_row("|cInitiative|n", fmt(data.get("initiative")))
    if data.get("primary_stats"):
        stats.add_row("|cStats|n", fmt(data.get("primary_stats")))
    if data.get("modifiers"):
        stats.add_row("|cModifiers|n", fmt(data.get("modifiers")))
    if data.get("buffs"):
        stats.add_row("|cBuffs|n", fmt(data.get("buffs")))
    lines.append("\n|cCombat Stats|n")
    lines.append(str(stats))

    flags = EvTable(border="cells")
    flags.add_row("|cAct Flags|n", fmt(data.get("actflags")))
    flags.add_row("|cAffects|n", fmt(data.get("affected_by")))
    flags.add_row("|cResists|n", fmt(data.get("ris")))
    if data.get("attack_types"):
        flags.add_row("|cAttacks|n", fmt(data.get("attack_types")))
    if data.get("defense_types"):
        flags.add_row("|cDefenses|n", fmt(data.get("defense_types")))
    lines.append("\n|cCombat Flags|n")
    lines.append(str(flags))

    rewards = EvTable(border="cells")
    rewards.add_row("|cXP Reward|n", fmt(data.get("exp_reward")))
    if "coin_drop" in data or "coins" in data:
        coins = data.get("coin_drop") or data.get("coins")
        if isinstance(coins, dict):
            from utils.currency import format_wallet

            coins = format_wallet(coins)
        rewards.add_row("|cCoin Drop|n", fmt(coins))
    if data.get("loot_table"):
        loot = []
        for e in data.get("loot_table"):
            part = f"{e.get('proto')}({e.get('chance', 100)}%)"
            if "guaranteed_after" in e:
                part += f" g:{e['guaranteed_after']}"
            loot.append(part)
        rewards.add_row("|cLoot Table|n", fmt(loot))
    lines.append("\n|cRewards|n")
    lines.append(str(rewards))

    skills = EvTable(border="cells")
    skills.add_row("|cSkills|n", fmt(data.get("skills")))
    skills.add_row("|cSpells|n", fmt(data.get("spells")))
    lines.append("\n|cSkills|n")
    lines.append(str(skills))

    return "\n".join(lines)


def with_summary(caller, text: str) -> str:
    """Prepend the current build summary to ``text``."""
    data = getattr(caller.ndb, "buildnpc", None)
    if not data:
        return text
    summary = format_mob_summary(data)
    return f"{summary}\n\n{text}"


# Menu nodes for NPC creation
def menunode_key(caller, raw_string="", **kwargs):
    """Prompt for the NPC key."""
    default = caller.ndb.buildnpc.get("key", "")
    text = "|wEnter NPC key|n"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wmerchant_01|n"
    options = add_back_skip({"key": "_default", "goto": _set_key}, _set_key)
    return with_summary(caller, text), options


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


def menunode_race(caller, raw_string="", **kwargs):
    """Prompt for the NPC race."""
    from world.mob_constants import NPC_RACES

    default = caller.ndb.buildnpc.get("race", "")
    options = add_back_skip({"key": "_default", "goto": _set_race}, _set_race)
    races = "/".join(r.value for r in NPC_RACES)
    text = f"|wRace|n ({races})"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |whuman|n"
    return with_summary(caller, text), options


def _set_race(caller, raw_string, **kwargs):
    from world.mob_constants import NPC_RACES

    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_desc"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("race", "")
    else:
        try:
            NPC_RACES.from_str(string)
        except ValueError:
            caller.msg(
                f"Invalid race. Choose from: {', '.join(r.value for r in NPC_RACES)}"
            )
            return "menunode_race"
    caller.ndb.buildnpc["race"] = string
    return "menunode_npc_class"


def menunode_sex(caller, raw_string="", **kwargs):
    """Prompt for the NPC sex."""
    from world.mob_constants import NPC_SEXES

    default = caller.ndb.buildnpc.get("sex", "")
    options = add_back_skip({"key": "_default", "goto": _set_sex}, _set_sex)
    sexes = "/".join(s.value for s in NPC_SEXES)
    text = f"|wSex|n ({sexes})"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wmale|n"
    return with_summary(caller, text), options


def _set_sex(caller, raw_string, **kwargs):
    from world.mob_constants import NPC_SEXES

    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_npc_class"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("sex", "")
    else:
        try:
            NPC_SEXES.from_str(string)
        except ValueError:
            caller.msg(
                f"Invalid sex. Choose from: {', '.join(s.value for s in NPC_SEXES)}"
            )
            return "menunode_sex"
    caller.ndb.buildnpc["sex"] = string
    return "menunode_weight"


def menunode_weight(caller, raw_string="", **kwargs):
    """Prompt for the NPC weight category."""
    from world.mob_constants import NPC_SIZES

    default = caller.ndb.buildnpc.get("weight", "")
    options = add_back_skip({"key": "_default", "goto": _set_weight}, _set_weight)
    sizes = "/".join(s.value for s in NPC_SIZES)
    text = f"|wWeight|n ({sizes})"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wmedium|n"
    return with_summary(caller, text), options


def _set_weight(caller, raw_string, **kwargs):
    from world.mob_constants import NPC_SIZES

    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_sex"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("weight", "")
    else:
        try:
            NPC_SIZES.from_str(string)
        except ValueError:
            caller.msg(
                f"Invalid weight. Choose from: {', '.join(s.value for s in NPC_SIZES)}"
            )
            return "menunode_weight"
    caller.ndb.buildnpc["weight"] = string
    return "menunode_level"


def menunode_desc(caller, raw_string="", **kwargs):
    """Prompt for a short description."""
    default = caller.ndb.buildnpc.get("desc", "")
    text = (
        "|wEnter a short description for the NPC|n "
        "(e.g. 'A grumpy orc')\n"
        "Type |wback|n to edit the key."
    )
    if default:
        text += f" [current: {default}]"
    options = add_back_only({"key": "_default", "goto": _set_desc}, _set_desc)
    return with_summary(caller, text), options


def _set_desc(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_key"
    if not string:
        caller.msg("Description is required.")
        return "menunode_desc"
    caller.ndb.buildnpc["desc"] = string
    return "menunode_race"


def menunode_vnum(caller, raw_string="", **kwargs):
    """Prompt for the NPC VNUM."""
    default = caller.ndb.buildnpc.get("vnum")
    text = dedent(
        """
        |wEnter VNUM or 'auto' to generate|n
        Example: |w123|n
    """
    )
    if default is not None:
        text += "(back to go back)"
        text += f" [current: {default}]"
    else:
        text += "(back to go back)"
    options = add_back_only({"key": "_default", "goto": _set_vnum}, _set_vnum)
    if default is None:
        options = list(options)

        def _auto(caller, raw_string=None, **kwargs):
            return _set_vnum(caller, "auto", **kwargs)

        options.insert(0, {"desc": "Auto", "goto": _auto})
    return with_summary(caller, text), options


def _set_vnum(caller, raw_string, **kwargs):
    string = str(raw_string).strip()
    if string.lower() == "back":
        return "menunode_desc"

    data = caller.ndb.buildnpc or {}

    if not string:
        caller.msg("VNUM is required.")
        return "menunode_vnum"
    if string.lower() == "auto":
        val = vnum_registry.get_next_vnum("npc")
    else:
        if not string.isdigit():
            caller.msg("Enter a number or 'auto'.")
            return "menunode_vnum"
        val = int(string)
        if not vnum_registry.validate_vnum(val, "npc"):
            caller.msg("Invalid or already used VNUM.")
            return "menunode_vnum"
        vnum_registry.register_vnum(val)

    data["vnum"] = val
    caller.ndb.buildnpc = data
    return "menunode_creature_type"


def menunode_role(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("role", "")
    types = "/".join(ALLOWED_ROLES_PRIMARY)
    text = dedent(
        f"""
        |wRole (merchant, questgiver...)|n ({types})
        Example: |wmerchant|n
        Type |wback|n to return.
        """
    )
    if default:
        text += f" [current: {default}]"
    options = add_back_only({"key": "_default", "goto": _set_role}, _set_role)
    return with_summary(caller, text), options


def _set_role(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    if string == "back":
        if caller.ndb.buildnpc.get("creature_type") == "unique":
            return "menunode_custom_slots"
        return "menunode_creature_type"
    if not string:
        caller.msg("Role is required.")
        return "menunode_role"
    if string and string not in ALLOWED_ROLES_PRIMARY:
        caller.msg(f"Invalid role. Choose from: {', '.join(ALLOWED_ROLES_PRIMARY)}")
        return "menunode_role"
    caller.ndb.buildnpc["role"] = string
    return "menunode_combat_class"


def menunode_guild_affiliation(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("guild_affiliation", "")
    text = "|wEnter guild tag for this receptionist|n"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wthieves_guild|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip(
        {"key": "_default", "goto": _set_guild_affiliation}, _set_guild_affiliation
    )
    return with_summary(caller, text), options


def _set_guild_affiliation(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        if not caller.ndb.buildnpc.get("role") and not caller.ndb.buildnpc.get("roles"):
            return "menunode_weight"
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
        Type |wback|n to return.
        """
    )
    if default:
        text += f" [current: {default}]"
    options = add_back_only(
        {"key": "_default", "goto": _set_creature_type}, _set_creature_type
    )
    return with_summary(caller, text), options


def _set_creature_type(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_vnum"
    if not string:
        caller.msg("Creature type is required.")
        return "menunode_creature_type"
    ctype = string.lower()
    caller.ndb.buildnpc["creature_type"] = ctype
    if ctype == "quadruped":
        caller.ndb.buildnpc["equipment_slots"] = [
            "head",
            "body",
            "front_legs",
            "hind_legs",
        ]
        return "menunode_role"
    if ctype == "unique":
        caller.ndb.buildnpc["equipment_slots"] = list(SLOT_ORDER)
        return "menunode_custom_slots"
    caller.ndb.buildnpc["equipment_slots"] = list(SLOT_ORDER)
    return "menunode_role"


def menunode_custom_slots(caller, raw_string="", **kwargs):
    slots = caller.ndb.buildnpc.get("equipment_slots", list(SLOT_ORDER))
    text = "|wEdit Equipment Slots|n\n"
    text += ", ".join(slots) if slots else "None"
    text += (
        "\nCommands:\n"
        "  add <slot> - add a slot\n"
        "  remove <slot> - remove a slot\n"
        "  done - finish editing\n"
        "  back - previous step\n"
        "Example: |wadd tail|n"
    )
    options = add_back_next(
        {"key": "_default", "goto": _edit_custom_slots}, _edit_custom_slots
    )
    return with_summary(caller, text), options


def _edit_custom_slots(caller, raw_string, **kwargs):
    string = raw_string.strip()
    slots = caller.ndb.buildnpc.setdefault("equipment_slots", list(SLOT_ORDER))
    if string.lower() == "back":
        return "menunode_creature_type"
    if string.lower() in ("done", "finish", "skip", ""):
        return "menunode_role"
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
    example = ", ".join(list(NPC_CLASS_MAP)[:3])
    text = f"|wNPC class ({example}...)|n ({classes})"
    if default:
        text += f" [default: {default}]"
    text += "\n(back to go back, next for default)"
    options = add_back_next({"key": "_default", "goto": _set_npc_class}, _set_npc_class)
    return with_summary(caller, text), options


def _set_npc_class(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    if string == "back":
        # if a role has been set, we came here from role selection
        if caller.ndb.buildnpc.get("role"):
            return "menunode_role"
        return "menunode_race"
    if not string or string in ("skip", "next"):
        string = caller.ndb.buildnpc.get("npc_class", "base")
    if string not in NPC_CLASS_MAP:
        caller.msg(f"Invalid class. Choose from: {', '.join(NPC_CLASS_MAP)}")
        return "menunode_npc_class"
    caller.ndb.buildnpc["npc_class"] = string

    return "menunode_sex"


def menunode_combat_class(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("combat_class", "")
    names = ", ".join(entry["name"] for entry in classes.CLASS_LIST)
    text = f"|wCombat class|n ({names})"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wWarrior|n"
    text += "\n(back to go back, next for default)"
    options = add_back_next(
        {"key": "_default", "goto": _set_combat_class}, _set_combat_class
    )
    return with_summary(caller, text), options


def _set_combat_class(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_npc_class"
    if not string or string.lower() in ("skip", "next"):
        string = caller.ndb.buildnpc.get("combat_class", "")
    else:
        names = [entry["name"].lower() for entry in classes.CLASS_LIST]
        if string.lower() not in names:
            caller.msg(
                "Invalid class. Choose from: "
                + ", ".join(entry["name"] for entry in classes.CLASS_LIST)
            )
            return "menunode_combat_class"
        for entry in classes.CLASS_LIST:
            if entry["name"].lower() == string.lower():
                string = entry["name"]
                break
    caller.ndb.buildnpc["combat_class"] = string
    _auto_fill_combat_stats(caller.ndb.buildnpc)
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
    return with_summary(caller, text), options


def _edit_roles(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    roles = caller.ndb.buildnpc.setdefault("roles", [])
    if string == "back":
        return "menunode_combat_class"
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
    if any(
        r in roles for r in ("guildmaster", "guild_receptionist")
    ) and not caller.ndb.buildnpc.get("guild_affiliation"):
        return "menunode_guild_affiliation"
    return "menunode_exp_reward"


def menunode_merchant_pricing(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("merchant_markup", 1.0)
    text = dedent(
        f"""
        |wMerchant price multiplier|n [default: {default}]
        Example: |w1.5|n
        (back to go back, skip for default)
        """
    )
    options = add_back_skip(
        {"key": "_default", "goto": _set_merchant_pricing}, _set_merchant_pricing
    )
    return with_summary(caller, text), options


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
        |wLevel of NPC (1-100)|n [current: {default}]
        Example: |w10|n
        (back to go back)
        """
    )
    options = add_back_only({"key": "_default", "goto": _set_level}, _set_level)
    return with_summary(caller, text), options


def _set_level(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_roles"
    if not string:
        caller.msg("Level is required.")
        return "menunode_level"
    try:
        val = int(string)
    except ValueError:
        caller.msg("Enter a number between 1 and 100.")
        return "menunode_level"
    if not 1 <= val <= 100:
        caller.msg("Enter a number between 1 and 100.")
        return "menunode_level"
    caller.ndb.buildnpc["level"] = val
    _auto_fill_combat_stats(caller.ndb.buildnpc)
    return "menunode_vnum"


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
    options = add_back_skip(
        {"key": "_default", "goto": _set_exp_reward}, _set_exp_reward
    )
    return with_summary(caller, text), options


def _set_exp_reward(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_role_details"
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
    return "menunode_coin_drop"


def menunode_coin_drop(caller, raw_string="", **kwargs):
    """Prompt for coin drop amounts."""
    from utils.currency import format_wallet, COIN_VALUES

    default = caller.ndb.buildnpc.get("coin_drop", {})
    text = "|wCoin drop|n (amount type pairs)"
    if default:
        text += f" [default: {format_wallet(default)}]"
    text += "\nExample: |w10 gold 5 silver|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_coin_drop}, _set_coin_drop)
    return with_summary(caller, text), options


def _set_coin_drop(caller, raw_string, **kwargs):
    from utils.currency import COIN_VALUES

    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_exp_reward"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("coin_drop", {})
    else:
        parts = string.split()
        if len(parts) % 2 != 0:
            caller.msg("Enter pairs like '10 gold 5 silver'.")
            return "menunode_coin_drop"
        val: dict[str, int] = {}
        for amt, coin in zip(parts[::2], parts[1::2]):
            if not amt.isdigit() or coin.lower() not in COIN_VALUES:
                caller.msg("Enter pairs like '10 gold 5 silver'.")
                return "menunode_coin_drop"
            val[coin.lower()] = val.get(coin.lower(), 0) + int(amt)
    caller.ndb.buildnpc["coin_drop"] = val
    return "menunode_loot_table"


def menunode_loot_table(caller, raw_string="", **kwargs):
    """Menu for editing loot table entries."""
    loot = caller.ndb.buildnpc.get("loot_table", [])
    text = "|wEdit Loot Table|n\n"
    if loot:
        for entry in loot:
            proto = entry.get("proto")
            chance = entry.get("chance", 100)
            guaranteed = entry.get("guaranteed_after")
            line = f" - {proto} ({chance}%)"
            if guaranteed is not None:
                line += f" g:{guaranteed}"
            text += line + "\n"
    else:
        text += "None\n"
    text += (
        "Commands:\n  add <proto> [chance] [guaranteed]\n  remove <proto>\n  done - finish\n  back - previous step\n"
        "Example: |wadd RAW_MEAT 50 3|n"
    )
    options = add_back_skip(
        {"key": "_default", "goto": _edit_loot_table}, _edit_loot_table
    )
    return with_summary(caller, text), options


def _edit_loot_table(caller, raw_string, **kwargs):
    string = raw_string.strip()
    table = caller.ndb.buildnpc.setdefault("loot_table", [])
    if string.lower() == "back":
        return "menunode_coin_drop"
    if string.lower() in ("done", "finish", "skip", ""):
        return "menunode_resources_prompt"
    if string.lower().startswith("add "):
        parts = string[4:].split()
        if not parts:
            caller.msg("Usage: add <proto> [chance] [guaranteed]")
            return "menunode_loot_table"
        proto = parts[0]
        chance = 100
        guaranteed = None
        if len(parts) > 1:
            if not parts[1].isdigit():
                caller.msg("Chance must be a number.")
                return "menunode_loot_table"
            chance = int(parts[1])
        if len(parts) > 2:
            if not parts[2].isdigit():
                caller.msg("Guaranteed count must be a number.")
                return "menunode_loot_table"
            guaranteed = int(parts[2])
        # check if entry exists
        for entry in table:
            if entry.get("proto") == proto:
                entry["chance"] = chance
                if guaranteed is not None:
                    entry["guaranteed_after"] = guaranteed
                else:
                    entry.pop("guaranteed_after", None)
                caller.msg(f"Updated {proto} ({chance}%).")
                break
        else:
            entry = {"proto": proto, "chance": chance}
            if guaranteed is not None:
                entry["guaranteed_after"] = guaranteed
            table.append(entry)
            caller.msg(f"Added {proto} ({chance}%).")
        return "menunode_loot_table"
    if string.lower().startswith("remove "):
        proto = string[7:].strip()
        for entry in list(table):
            if entry.get("proto") == proto:
                table.remove(entry)
                caller.msg(f"Removed {proto}.")
                break
        else:
            caller.msg("Entry not found.")
        return "menunode_loot_table"
    caller.msg("Unknown command.")
    return "menunode_loot_table"


def menunode_resources_prompt(caller, raw_string="", **kwargs):
    """Ask if custom HP/MP/SP should be entered."""
    text = dedent(
        """
        |wWould you like to enter specific HP/MP/SP or use default?|n
        Type |w1|n for default or |w2|n to enter values.
        """
    )
    options = [
        {"key": ("1", "default"), "goto": _use_default_resources},
        {"key": ("2", "custom"), "goto": "menunode_resources"},
        {"desc": "Back", "goto": "menunode_loot_table"},
    ]
    return with_summary(caller, text), options


def _preview(caller):
    """Send a summary preview of current build data."""
    data = getattr(caller.ndb, "buildnpc", None)
    if data:
        caller.msg(format_mob_summary(data))


def _use_default_resources(caller, raw_string, **kwargs):
    caller.ndb.buildnpc.pop("hp", None)
    caller.ndb.buildnpc.pop("mp", None)
    caller.ndb.buildnpc.pop("sp", None)
    _preview(caller)
    return "menunode_combat_values"


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
    return with_summary(caller, text), options


def _set_resources(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_resources_prompt"
    if not string or string.lower() == "skip":
        caller.ndb.buildnpc["hp"] = caller.ndb.buildnpc.get("hp", 0)
        caller.ndb.buildnpc["mp"] = caller.ndb.buildnpc.get("mp", 0)
        caller.ndb.buildnpc["sp"] = caller.ndb.buildnpc.get("sp", 0)
        _preview(caller)
        return "menunode_combat_values"
    parts = string.split()
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        caller.msg("Enter three numbers separated by spaces.")
        return "menunode_resources"
    caller.ndb.buildnpc["hp"] = int(parts[0])
    caller.ndb.buildnpc["mp"] = int(parts[1])
    caller.ndb.buildnpc["sp"] = int(parts[2])
    _preview(caller)
    return "menunode_combat_values"


def menunode_combat_values(caller, raw_string="", **kwargs):
    """Prompt for base damage, armor and initiative."""
    dmg = caller.ndb.buildnpc.get("damage", 1)
    armor = caller.ndb.buildnpc.get("armor", 0)
    init = caller.ndb.buildnpc.get("initiative", 0)
    default = f"{dmg} {armor} {init}"
    text = dedent(
        f"""
        |wEnter Damage Armor Initiative|n [default: {default}]
        Example: |w5 2 10|n
        (back to go back, skip for default)
        """
    )
    options = add_back_skip({"key": "_default", "goto": _set_combat_values}, _set_combat_values)
    return with_summary(caller, text), options


def _set_combat_values(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_resources_prompt"
    if not string or string.lower() == "skip":
        caller.ndb.buildnpc["damage"] = caller.ndb.buildnpc.get("damage", 1)
        caller.ndb.buildnpc["armor"] = caller.ndb.buildnpc.get("armor", 0)
        caller.ndb.buildnpc["initiative"] = caller.ndb.buildnpc.get("initiative", 0)
        _preview(caller)
        return "menunode_modifiers"
    parts = string.split()
    if len(parts) != 3 or not all(p.lstrip("-+").isdigit() for p in parts):
        caller.msg("Enter three numbers separated by spaces.")
        return "menunode_combat_values"
    caller.ndb.buildnpc["damage"] = int(parts[0])
    caller.ndb.buildnpc["armor"] = int(parts[1])
    caller.ndb.buildnpc["initiative"] = int(parts[2])
    _preview(caller)
    return "menunode_modifiers"


def menunode_modifiers(caller, raw_string="", **kwargs):
    """Prompt for stat modifiers and buffs."""
    mods = caller.ndb.buildnpc.get("modifiers", {})
    buffs = caller.ndb.buildnpc.get("buffs", [])
    mod_text = ", ".join(f"{k}+{v}" for k, v in mods.items()) if mods else ""
    buff_text = ", ".join(buffs)
    default = ", ".join(filter(None, [mod_text, buff_text]))
    text = "|wEnter modifiers and buffs/debuffs|n"
    if default:
        text += f" [default: {default}]"
    text += "\nUse form 'STR+1, DEX-2, haste, slow'"
    text += "\n(back to go back, skip for none)"
    options = add_back_skip({"key": "_default", "goto": _set_modifiers}, _set_modifiers)
    return with_summary(caller, text), options


def _set_modifiers(caller, raw_string, **kwargs):
    from commands.admin import parse_stat_mods

    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_combat_values"
    if not string or string.lower() == "skip":
        caller.ndb.buildnpc["modifiers"] = caller.ndb.buildnpc.get("modifiers", {})
        caller.ndb.buildnpc["buffs"] = caller.ndb.buildnpc.get("buffs", [])
        _preview(caller)
        return "menunode_secondary_stats_prompt"
    try:
        mods, remainder = parse_stat_mods(string)
    except ValueError as err:
        caller.msg(f"Invalid modifier: {err}")
        return "menunode_modifiers"
    buffs = []
    if remainder:
        buffs = [p.strip() for p in remainder.split(",") if p.strip()]
    caller.ndb.buildnpc["modifiers"] = mods
    caller.ndb.buildnpc["buffs"] = buffs
    _preview(caller)
    return "menunode_secondary_stats_prompt"


def menunode_secondary_stats_prompt(caller, raw_string="", **kwargs):
    """Ask if custom primary stats should be entered."""

    text = dedent(
        """
        |wUse default STR/CON/etc or enter custom values?|n
        Type |w1|n for defaults or |w2|n to enter values.
        """
    )
    options = [
        {"key": ("1", "default"), "goto": _use_default_stats},
        {"key": ("2", "custom"), "goto": "menunode_stats"},
        {"desc": "Back", "goto": "menunode_modifiers"},
    ]
    return with_summary(caller, text), options


def _use_default_stats(caller, raw_string, **kwargs):
    stats = ["STR", "CON", "DEX", "INT", "WIS", "LUCK"]
    caller.ndb.buildnpc["primary_stats"] = {
        stat: caller.ndb.buildnpc.get("primary_stats", {}).get(stat, 0)
        for stat in stats
    }
    _preview(caller)
    return "menunode_behavior"


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
    return with_summary(caller, text), options


def _set_stats(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_modifiers"
    stats = ["STR", "CON", "DEX", "INT", "WIS", "LUCK"]
    if not string or string.lower() == "skip":
        caller.ndb.buildnpc["primary_stats"] = {
            stat: caller.ndb.buildnpc.get("primary_stats", {}).get(stat, 0)
            for stat in stats
        }
        _preview(caller)
        return "menunode_behavior"
    parts = string.split()
    if len(parts) != 6 or not all(p.isdigit() for p in parts):
        caller.msg("Enter six numbers separated by spaces.")
        return "menunode_stats"
    caller.ndb.buildnpc["primary_stats"] = {
        stat: int(val) for stat, val in zip(stats, parts)
    }
    _preview(caller)
    return "menunode_behavior"


def menunode_behavior(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("behavior", "")
    text = "|wDescribe basic behavior or reactions|n"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wSells potions and greets players|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_behavior}, _set_behavior)
    return with_summary(caller, text), options


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
    npc_class = caller.ndb.buildnpc.get("npc_class", "base")
    suggested = ", ".join(get_skills_for_class(npc_class))
    text = "|wList any skills or attacks (comma separated)|n"
    if default:
        text += f" [default: {default}]"
    text += f"\nSuggested for {npc_class}: {suggested}"
    text += "\nExample: |wfireball, slash, heal|n"
    text += "\n(back to go back, skip for default)"
    options = add_back_skip({"key": "_default", "goto": _set_skills}, _set_skills)
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


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
    return with_summary(caller, text), options


def menunode_trigger_list(caller, raw_string="", **kwargs):
    """Show all triggers."""
    mobprogs = caller.ndb.buildnpc.get("mobprogs") or []
    text = "|wCurrent MobProgs|n\n"
    if mobprogs:
        for idx, prog in enumerate(mobprogs, 1):
            cond = prog.get("conditions") or {}
            match = cond.get("match", "")
            resp = prog.get("commands") or []
            if isinstance(resp, list):
                resp = ", ".join(resp)
            text += f'{idx}. {prog.get("type")}: "{match}" -> {resp}\n'
    else:
        text += "None\n"
    options = [{"desc": "Back", "goto": "menunode_triggers"}]
    return with_summary(caller, text), options


def menunode_trigger_add(caller, raw_string="", **kwargs):
    """Choose trigger event type."""
    text = "|wSelect event type|n"
    options = [
        {"desc": "on_enter", "goto": (_set_trigger_event, {"event": "on_enter"})},
        {"desc": "on_speak", "goto": (_set_trigger_event, {"event": "on_speak"})},
        {"desc": "on_attack", "goto": (_set_trigger_event, {"event": "on_attack"})},
        {
            "desc": "on_give_item",
            "goto": (_set_trigger_event, {"event": "on_give_item"}),
        },
        {"desc": "on_look", "goto": (_set_trigger_event, {"event": "on_look"})},
        {"desc": "on_timer", "goto": (_set_trigger_event, {"event": "on_timer"})},
        {"desc": "custom", "goto": "menunode_trigger_custom"},
        {"desc": "Back", "goto": "menunode_triggers"},
    ]
    return with_summary(caller, text), options


def menunode_trigger_custom(caller, raw_string="", **kwargs):
    """Prompt for custom event name."""
    text = "|wEnter custom event name|n"
    options = add_back_skip(
        {"key": "_default", "goto": _set_custom_event}, _set_custom_event
    )
    return with_summary(caller, text), options


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
    options = add_back_skip(
        {"key": "_default", "goto": _set_trigger_match}, _set_trigger_match
    )
    return with_summary(caller, text), options


def _set_trigger_match(caller, raw_string, **kwargs):
    caller.ndb.trigger_match = raw_string.strip()
    return "menunode_trigger_react"


def menunode_trigger_react(caller, raw_string="", **kwargs):
    text = "|wEnter reaction command(s) (comma or semicolon separated)|n"
    options = add_back_skip({"key": "_default", "goto": _save_trigger}, _save_trigger)
    return with_summary(caller, text), options


def _save_trigger(caller, raw_string, **kwargs):
    reaction = raw_string.strip()
    event = caller.ndb.trigger_event
    match = caller.ndb.trigger_match
    mobprogs = caller.ndb.buildnpc.setdefault("mobprogs", [])

    responses = [part.strip() for part in re.split(r"[;,]", reaction) if part.strip()]
    prog = {"type": event, "conditions": {}, "commands": responses}
    if match:
        prog["conditions"]["match"] = match
    mobprogs.append(prog)
    caller.ndb.trigger_event = None
    caller.ndb.trigger_match = None
    caller.msg("MobProg added.")
    return "menunode_triggers"


def menunode_trigger_delete(caller, raw_string="", **kwargs):
    """Select trigger to delete."""
    mobprogs = caller.ndb.buildnpc.get("mobprogs") or []
    if not mobprogs:
        caller.msg("No mobprogs to delete.")
        return "menunode_triggers"
    text = "|wSelect trigger to delete|n"
    options = []
    for idx, prog in enumerate(mobprogs):
        cond = prog.get("conditions") or {}
        match = cond.get("match", "")
        resp = prog.get("commands") or []
        if isinstance(resp, list):
            resp = ", ".join(resp)
        desc = f'{idx}: {prog.get("type")}: "{match}" -> {resp}'
        options.append({"desc": desc, "goto": (_del_trigger, {"index": idx})})
    options.append({"desc": "Back", "goto": "menunode_triggers"})
    return with_summary(caller, text), options


def _del_trigger(caller, raw_string, event=None, index=None, **kwargs):
    mobprogs = caller.ndb.buildnpc.get("mobprogs") or []
    if index is not None and 0 <= index < len(mobprogs):
        mobprogs.pop(index)
        caller.msg("MobProg removed.")
    return "menunode_triggers"


def menunode_confirm(caller, raw_string="", **kwargs):
    data = caller.ndb.buildnpc
    required_key = {"key"}
    if not isinstance(data, dict) or not required_key.issubset(data):
        caller.msg("Error: NPC data incomplete. Restarting builder.")
        return None

    required_fields = {
        "desc": "menunode_desc",
        "vnum": "menunode_vnum",
        "creature_type": "menunode_creature_type",
        "role": "menunode_role",
        "level": "menunode_level",
    }

    for field, node in required_fields.items():
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val):
            caller.msg(f"{field.replace('_', ' ').capitalize()} is required.")
            return node

    text = "|wConfirm NPC Creation|n\n"
    text += format_mob_summary(data) + "\n"

    warnings = validate_prototype(data)
    if warnings:
        text += "|yWarnings:|n\n"
        for warn in warnings:
            text += f" - {warn}\n"

    text += (
        "\nCreate this NPC?\n"
        "Selecting |wYes|n spawns the NPC in your current location.\n"
        "Selecting |wYes & Save Prototype|n spawns the NPC and saves the prototype for later use."
    )
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
    tclass_path = NPC_CLASS_MAP.get(
        data.get("npc_class", "base"), "typeclasses.npcs.BaseNPC"
    )
    if data.get("edit_obj"):
        npc = data.get("edit_obj")
        if npc.typeclass_path != tclass_path:
            npc.swap_typeclass(tclass_path, clean_attributes=False)
    else:
        npc = create_object(tclass_path, key=data.get("key"), location=caller.location)
    npc.db.desc = data.get("desc")
    npc.db.race = data.get("race")
    npc.db.sex = data.get("sex")
    npc.db.weight = data.get("weight")
    if cc := data.get("combat_class"):
        npc.db.charclass = cc
        npc.db.combat_class = cc
    if vnum := data.get("vnum"):
        npc.db.vnum = vnum
        npc.tags.add(f"M{vnum}", category="vnum")
    npc.tags.add("npc")
    role = data.get("role") or data.get("npc_type")
    if role:
        npc.tags.add(role, category="npc_type")
        npc.tags.add(role, category="npc_role")
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
    npc.db.modifiers = data.get("modifiers") or {}
    npc.db.buffs = data.get("buffs") or []
    mobprogs = data.get("mobprogs") or []
    npc.db.mobprogs = mobprogs
    npc.db.triggers = mobprogs_to_triggers(mobprogs)
    npc.db.coin_drop = data.get("coin_drop") or {}
    npc.db.loot_table = data.get("loot_table") or []
    npc.db.exp_reward = data.get("exp_reward", 0)
    if script_path := data.get("script"):
        try:
            script_cls = _import_script(script_path)
            npc.scripts.add(script_cls, key=script_cls.__name__)
        except ImportError as err:
            logger.log_err(f"Script import rejected in npc builder: {err}")
            caller.msg(f"Module not allowed for script: {script_path}")
        except Exception as err:  # pragma: no cover - log errors
            caller.msg(f"Could not attach script {script_path}: {err}")
    npc.db.creature_type = data.get("creature_type")
    if data.get("use_mob"):
        npc.db.can_attack = True
        if not npc.db.natural_weapon:
            npc.db.natural_weapon = {
                "name": "fists",
                "damage_type": "bash",
                "damage": data.get("damage", 1),
                "speed": 10,
                "stamina_cost": 5,
            }
        else:
            npc.db.natural_weapon["damage"] = data.get("damage", npc.db.natural_weapon.get("damage", 1))
    else:
        if data.get("damage") is not None:
            npc.db.natural_weapon = npc.db.natural_weapon or {
                "name": "fists",
                "damage_type": "bash",
                "speed": 10,
                "stamina_cost": 5,
            }
            npc.db.natural_weapon["damage"] = data.get("damage")
    npc.db.armor = data.get("armor", 0)
    if npc.traits.get("armor"):
        npc.traits.armor.base = data.get("armor", 0)
    if npc.traits.get("initiative"):
        npc.traits.initiative.base = data.get("initiative", 0)
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
        if data.get("vnum") is not None:
            proto["vnum"] = data.get("vnum")
        if data.get("coin_drop"):
            proto["coin_drop"] = data.get("coin_drop")
        if data.get("loot_table"):
            proto["loot_table"] = data.get("loot_table")
        if data.get("mobprogs"):
            proto["mobprogs"] = data.get("mobprogs")
        proto["damage"] = data.get("damage", 1)
        proto["armor"] = data.get("armor", 0)
        proto["initiative"] = data.get("initiative", 0)
        if data.get("use_mob"):
            proto["can_attack"] = True
            proto.setdefault(
                "natural_weapon",
                {
                    "name": "fists",
                    "damage_type": "bash",
                    "damage": data.get("damage", 1),
                    "speed": 10,
                    "stamina_cost": 5,
                },
            )
        if data.get("script"):
            proto["scripts"] = [data["script"]]
        prototypes.register_npc_prototype(proto_key, proto)
        if data.get("vnum") is not None:
            from world.scripts.mob_db import get_mobdb

            get_mobdb().add_proto(data["vnum"], proto)
        area = caller.location.db.area
        if area:
            from world import area_npcs

            area_npcs.add_area_npc(area, proto_key)
        caller.msg(f"NPC {npc.key} created and prototype saved.")
    else:
        caller.msg(f"NPC {npc.key} created.")
    finalize_mob_prototype(caller, npc)
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
        "race": npc.db.race or "",
        "sex": npc.db.sex or "",
        "weight": npc.db.weight or "",
        "role": npc.tags.get(category="npc_type") or "",
        "roles": [
            t
            for t in npc.tags.get(category="npc_role", return_list=True) or []
            if t != npc.tags.get(category="npc_type")
        ],
        "npc_class": next(
            (k for k, path in NPC_CLASS_MAP.items() if path == npc.typeclass_path),
            "base",
        ),
        "combat_class": npc.db.charclass or "",
        "creature_type": npc.db.creature_type or "humanoid",
        "equipment_slots": npc.db.equipment_slots or list(SLOT_ORDER),
        "level": npc.db.level or 1,
        "hp": npc.traits.health.base if npc.traits.get("health") else 0,
        "mp": npc.traits.mana.base if npc.traits.get("mana") else 0,
        "sp": npc.traits.stamina.base if npc.traits.get("stamina") else 0,
        "damage": npc.db.natural_weapon.get("damage", 1) if npc.db.natural_weapon else 1,
        "armor": npc.db.armor or 0,
        "initiative": getattr(npc.traits.get("initiative"), "base", 0),
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
        "coin_drop": npc.db.coin_drop or {},
        "loot_table": npc.db.loot_table or [],
        "merchant_markup": npc.db.merchant_markup or 1.0,
        "guild_affiliation": npc.tags.get(category="guild_affiliation") or "",
        "mobprogs": npc.db.mobprogs or [],
        "script": next(
            (scr.typeclass_path for scr in npc.scripts.all() if scr.key != "npc_ai"), ""
        ),
        "modifiers": npc.db.modifiers or {},
        "buffs": npc.db.buffs or [],
    }


def finalize_mob_prototype(caller, npc):
    """Finalize ``npc`` with default combat stats and register it."""
    if not npc.db.level or not npc.db.combat_class:
        caller.msg("|rCannot finalize mob. Missing level or class.|n")
        return

    npc.db.charclass = npc.db.combat_class
    stats = calculate_combat_stats(npc.db.combat_class, npc.db.level)
    npc.db.hp = stats["hp"]
    npc.db.mp = stats["mp"]
    npc.db.sp = stats["sp"]
    npc.db.armor = stats["armor"]
    npc.db.initiative = stats["initiative"]

    from world.mobregistry import register_mob_vnum

    if npc.db.vnum:
        register_mob_vnum(vnum=npc.db.vnum, prototype=npc)

    caller.msg(
        f"|gMob '{npc.key}' finalized with VNUM {npc.db.vnum} and added to mob list.|n"
    )


class CmdCNPC(Command):
    """Create or edit an NPC using a guided menu."""

    key = "cnpc"
    aliases = ["createnpc", "mobbuilder"]
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg(
                "Usage: cnpc start <key> | cnpc edit <npc> | cnpc dev_spawn <proto>"
            )
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
                "race": "",
                "sex": "",
                "weight": "",
                "mobprogs": [],
                "npc_class": "base",
                "combat_class": "",
                "roles": [],
                "skills": [],
                "spells": [],
                "ris": [],
                "coin_drop": {},
                "loot_table": [],
                "exp_reward": 0,
                "damage": 1,
                "armor": 0,
                "initiative": 0,
                "merchant_markup": 1.0,
                "script": "",
                "modifiers": {},
                "buffs": [],
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
