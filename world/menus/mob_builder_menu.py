"""Menu nodes for NPC builder."""

# Import necessary utilities and helpers from commands.npc_builder
from commands import npc_builder

from utils.menu_utils import (
    add_back_skip,
    add_back_next,
    add_back_only,
    toggle_multi_select,
    format_multi_select,
)
from utils import vnum_registry
from utils.prototype_manager import load_prototype
from world.areas import find_area_by_vnum
from evennia.utils import dedent
import re

# Expose some frequently used constants locally
NPCType = npc_builder.NPCType
NPC_TYPE_MAP = npc_builder.NPC_TYPE_MAP
COMBATANT_TYPES = npc_builder.COMBATANT_TYPES
ALLOWED_ROLES = npc_builder.ALLOWED_ROLES
ALLOWED_AI_TYPES = npc_builder.ALLOWED_AI_TYPES
REVIEW_SECTIONS = npc_builder.REVIEW_SECTIONS

# bring helper functions into namespace

# many menunode helper setters are reused directly
_auto_fill_combat_stats = npc_builder._auto_fill_combat_stats
_cancel = npc_builder._cancel
_create_npc = npc_builder._create_npc
validate_prototype = npc_builder.validate_prototype
format_mob_summary = npc_builder.format_mob_summary
def with_summary(caller, text: str) -> str:
    """Prepend the current build summary to ``text``."""
    data = getattr(caller.ndb, "buildnpc", None)
    if not data:
        return text
    summary = format_mob_summary(data)
    return f"{summary}\n\n{text}"


def _next_node(caller, default: str) -> str:
    """Return ``default`` unless editing from review."""
    ret = getattr(caller.ndb, "return_to", None)
    if ret:
        del caller.ndb.return_to
        return ret
    return default


def _goto_section(caller, raw_string, node=None, **kwargs):
    """Helper for jumping to ``node`` while remembering to return."""
    caller.ndb.return_to = "menunode_review"
    return node


# Menu nodes for NPC creation
def menunode_key(caller, raw_string="", **kwargs):
    """Prompt for the NPC key."""
    default = caller.ndb.buildnpc.get("key", "")
    text = "|wEnter NPC key|n"
    text += "\n(Prototype = saved blueprint; archetype/NPC type defines role)"
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
    return _next_node(caller, "menunode_desc")


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
        return "menunode_level"
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
    return _next_node(caller, "menunode_npc_type")


def menunode_gender(caller, raw_string="", **kwargs):
    """Prompt for the NPC gender."""
    from world.mob_constants import NPC_GENDERS

    default = caller.ndb.buildnpc.get("gender", "")
    options = add_back_skip({"key": "_default", "goto": _set_gender}, _set_gender)
    sexes = "/".join(s.value for s in NPC_GENDERS)
    text = f"|wGender|n ({sexes})"
    if default:
        text += f" [default: {default}]"
    text += "\nExample: |wmale|n"
    return with_summary(caller, text), options


def _set_gender(caller, raw_string, **kwargs):
    from world.mob_constants import NPC_GENDERS

    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_npc_type"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("gender", "")
    else:
        try:
            NPC_GENDERS.from_str(string)
        except ValueError:
            caller.msg(
                f"Invalid gender. Choose from: {', '.join(s.value for s in NPC_GENDERS)}"
            )
            return "menunode_gender"
    caller.ndb.buildnpc["gender"] = string
    return _next_node(caller, "menunode_weight")


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
        return "menunode_gender"
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
    next_step = "menunode_creature_type" if caller.ndb.buildnpc.get("vnum") is not None else "menunode_vnum"
    return _next_node(caller, next_step)


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
    return _next_node(caller, "menunode_longdesc")


def menunode_longdesc(caller, raw_string="", **kwargs):
    """Prompt for a long description."""
    default = caller.ndb.buildnpc.get("long_desc", "")
    text = "|wEnter a long description for the NPC|n"
    if default:
        text += f" [current: {default}]"
    text += "\n(back to go back)"
    options = add_back_only({"key": "_default", "goto": _set_longdesc}, _set_longdesc)
    return with_summary(caller, text), options


def _set_longdesc(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_weight"
    if not string:
        caller.msg("Long description is required.")
        return "menunode_longdesc"
    caller.ndb.buildnpc["long_desc"] = string
    return _next_node(caller, "menunode_level")


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
        return "menunode_weight"

    data = caller.ndb.buildnpc or {}
    old = data.get("vnum")

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

    if old is not None and old != val:
        vnum_registry.unregister_vnum(int(old), "npc")

    data["vnum"] = val
    if area := find_area_by_vnum(val):
        data.setdefault("area", area.key)
    caller.ndb.buildnpc = data
    return _next_node(caller, "menunode_creature_type")


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
        return "menunode_roles"
    if not string or string.lower() == "skip":
        string = caller.ndb.buildnpc.get("guild_affiliation", "")
    caller.ndb.buildnpc["guild_affiliation"] = string
    return _next_node(caller, "menunode_role_details")


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
        next_node = (
            "menunode_combat_class"
            if caller.ndb.buildnpc.get("npc_type", NPCType.BASE) in COMBATANT_TYPES
            else "menunode_roles"
        )
        return _next_node(caller, next_node)
    if ctype == "unique":
        caller.ndb.buildnpc["equipment_slots"] = list(SLOT_ORDER)
        return _next_node(caller, "menunode_custom_slots")
    caller.ndb.buildnpc["equipment_slots"] = list(SLOT_ORDER)
    next_node = (
        "menunode_combat_class"
        if caller.ndb.buildnpc.get("npc_type", NPCType.BASE) in COMBATANT_TYPES
        else "menunode_roles"
    )
    return _next_node(caller, next_node)


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
        next_node = (
            "menunode_combat_class"
            if caller.ndb.buildnpc.get("npc_type", NPCType.BASE) in COMBATANT_TYPES
            else "menunode_roles"
        )
        return _next_node(caller, next_node)
    if string.lower().startswith("add "):
        slot = string[4:].strip().lower()
        if slot and slot not in slots:
            slots.append(slot)
            caller.msg(f"Added {slot} slot.")
        else:
            caller.msg("Slot already present or invalid.")
        return _next_node(caller, "menunode_custom_slots")
    if string.lower().startswith("remove "):
        slot = string[7:].strip().lower()
        if slot in slots:
            slots.remove(slot)
            caller.msg(f"Removed {slot} slot.")
        else:
            caller.msg("Slot not found.")
        return _next_node(caller, "menunode_custom_slots")
    caller.msg("Unknown command.")
    return _next_node(caller, "menunode_custom_slots")


def menunode_npc_type(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("npc_type", NPCType.BASE)
    classes = "/".join(t.value for t in NPC_TYPE_MAP)
    example = ", ".join(t.value for t in list(NPC_TYPE_MAP)[:3])
    text = f"|wNPC Type/Archetype|n ({classes})"
    if default:
        text += f" [default: {default}]"
    text += f"\nChoose the NPC's general role, e.g. |w{example}|n"
    text += "\n(back to go back, next for default)"
    options = add_back_next({"key": "_default", "goto": _set_npc_type}, _set_npc_type)
    return with_summary(caller, text), options


def _set_npc_type(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_race"
    if not string or string.lower() in ("skip", "next"):
        npc_type = caller.ndb.buildnpc.get("npc_type", NPCType.BASE)
    else:
        try:
            npc_type = NPCType.from_str(string)
        except ValueError:
            caller.msg(
                f"Invalid NPC type. Choose from: {', '.join(t.value for t in NPCType)}"
            )
            return "menunode_npc_type"
    if npc_type not in NPC_TYPE_MAP:
        caller.msg(
            f"Invalid class. Choose from: {', '.join(t.value for t in NPC_TYPE_MAP)}"
        )
        return "menunode_npc_type"
    caller.ndb.buildnpc["npc_type"] = npc_type

    return _next_node(caller, "menunode_gender")


def menunode_combat_class(caller, raw_string="", **kwargs):
    if caller.ndb.buildnpc.get("npc_type", NPCType.BASE) not in COMBATANT_TYPES:
        return menunode_roles(caller)

    default = caller.ndb.buildnpc.get("combat_class", "")
    names = ", ".join(entry["name"] for entry in classes.CLASS_LIST)
    text = f"|wCombat Class|n ({names})"
    if default:
        text += f" [default: {default}]"
    text += "\nChoose a combat specialization."
    text += "\nExample: |wWarrior|n"
    text += "\n(back to go back, next for default)"
    options = add_back_next(
        {"key": "_default", "goto": _set_combat_class}, _set_combat_class
    )
    return with_summary(caller, text), options


def _set_combat_class(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_npc_type"
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
    return _next_node(caller, "menunode_roles")


def menunode_roles(caller, raw_string="", **kwargs):
    roles = caller.ndb.buildnpc.get("roles", [])
    text = "|wEdit NPC Roles|n\n"
    text += format_multi_select(ALLOWED_ROLES, roles)
    text += (
        "\nSelect a number or role name to toggle.\n"
        "done - finish, back - previous step"
    )
    options = add_back_skip({"key": "_default", "goto": _edit_roles}, _edit_roles)
    return with_summary(caller, text), options


def _edit_roles(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    roles = caller.ndb.buildnpc.setdefault("roles", [])
    if string == "back":
        if caller.ndb.buildnpc.get("npc_type", NPCType.BASE) in COMBATANT_TYPES:
            return "menunode_combat_class"
        if caller.ndb.buildnpc.get("creature_type") == "unique":
            return "menunode_custom_slots"
        return "menunode_creature_type"
    if string in ("done", "finish", "skip", ""):
        return _next_node(caller, "menunode_role_details")
    if toggle_multi_select(string, ALLOWED_ROLES, roles):
        return "menunode_roles"
    caller.msg("Invalid selection.")
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
        return "menunode_longdesc"
    if not string or string.lower() == "skip":
        val = caller.ndb.buildnpc.get("merchant_markup", 1.0)
    else:
        try:
            val = float(string)
        except ValueError:
            caller.msg("Enter a number.")
            return "menunode_merchant_pricing"
    caller.ndb.buildnpc["merchant_markup"] = val
    return _next_node(caller, "menunode_role_details")


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
        return "menunode_longdesc"
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
    return _next_node(caller, "menunode_race")


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
        Leave blank for level \xd7 DEFAULT_XP_PER_LEVEL
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
    return _next_node(caller, "menunode_coin_drop")


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
    return _next_node(caller, "menunode_loot_table")


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
        "Commands:\n  add <proto> [chance] [amount] [guaranteed]\n  remove <proto>\n  done - finish\n  back - previous step\n"
        "Example: |wadd 100001 50|n, |wadd gold 100 5|n"
    )
    options = add_back_skip(
        {"key": "_default", "goto": _edit_loot_table}, _edit_loot_table
    )
    return with_summary(caller, text), options


def _edit_loot_table(caller, raw_string, **kwargs):
    from utils.currency import COIN_VALUES

    string = raw_string.strip()
    table = caller.ndb.buildnpc.setdefault("loot_table", [])
    if string.lower() == "back":
        return "menunode_coin_drop"
    if string.lower() in ("done", "finish", "skip", ""):
        return _next_node(caller, "menunode_resources_prompt")
    if string.lower().startswith("add "):
        parts = string[4:].split()
        if not parts:
            caller.msg("Usage: add <proto> [chance] [amount] [guaranteed]")
            return "menunode_loot_table"
        proto = parts[0]
        if proto.isdigit():
            vnum = int(proto)
            if not vnum_registry.VNUM_RANGES["object"][0] <= vnum <= vnum_registry.VNUM_RANGES["object"][1]:
                caller.msg("Invalid object VNUM.")
                return "menunode_loot_table"
            if not load_prototype("object", vnum):
                caller.msg("Unknown object VNUM.")
                return "menunode_loot_table"
            proto = vnum
        chance = 100
        amount = 1
        guaranteed = None
        if len(parts) > 1:
            if not parts[1].isdigit():
                caller.msg("Chance must be a number.")
                return "menunode_loot_table"
            chance = int(parts[1])
        if isinstance(proto, str) and proto.lower() in COIN_VALUES and len(parts) > 2:
            if not parts[2].isdigit():
                caller.msg("Amount must be a number.")
                return "menunode_loot_table"
            amount = int(parts[2])
            if len(parts) > 3:
                if not parts[3].isdigit():
                    caller.msg("Guaranteed count must be a number.")
                    return "menunode_loot_table"
                guaranteed = int(parts[3])
        elif len(parts) > 2:
            if not parts[2].isdigit():
                caller.msg("Guaranteed count must be a number.")
                return "menunode_loot_table"
            guaranteed = int(parts[2])
        # check if entry exists
        for entry in table:
            if entry.get("proto") == proto:
                entry["chance"] = chance
                if isinstance(proto, str) and proto.lower() in COIN_VALUES:
                    entry["amount"] = amount
                if guaranteed is not None:
                    entry["guaranteed_after"] = guaranteed
                else:
                    entry.pop("guaranteed_after", None)
                caller.msg(f"Updated {proto} ({chance}%).")
                break
        else:
            entry = {"proto": proto, "chance": chance}
            if isinstance(proto, str) and proto.lower() in COIN_VALUES:
                entry["amount"] = amount
            if guaranteed is not None:
                entry["guaranteed_after"] = guaranteed
            table.append(entry)
            caller.msg(f"Added {proto} ({chance}%).")
        return _next_node(caller, "menunode_loot_table")
    if string.lower().startswith("remove "):
        proto = string[7:].strip()
        if proto.isdigit():
            proto = int(proto)
        for entry in list(table):
            if entry.get("proto") == proto:
                table.remove(entry)
                caller.msg(f"Removed {proto}.")
                break
        else:
            caller.msg("Entry not found.")
        return _next_node(caller, "menunode_loot_table")
    caller.msg("Unknown command.")
    return _next_node(caller, "menunode_loot_table")


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
    return _next_node(caller, "menunode_combat_values")


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
        return _next_node(caller, "menunode_combat_values")
    parts = string.split()
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        caller.msg("Enter three numbers separated by spaces.")
        return "menunode_resources"
    caller.ndb.buildnpc["hp"] = int(parts[0])
    caller.ndb.buildnpc["mp"] = int(parts[1])
    caller.ndb.buildnpc["sp"] = int(parts[2])
    _preview(caller)
    return _next_node(caller, "menunode_combat_values")


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
    options = add_back_skip(
        {"key": "_default", "goto": _set_combat_values}, _set_combat_values
    )
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
        return _next_node(caller, "menunode_modifiers")
    parts = string.split()
    if len(parts) != 3 or not all(p.lstrip("-+").isdigit() for p in parts):
        caller.msg("Enter three numbers separated by spaces.")
        return "menunode_combat_values"
    caller.ndb.buildnpc["damage"] = int(parts[0])
    caller.ndb.buildnpc["armor"] = int(parts[1])
    caller.ndb.buildnpc["initiative"] = int(parts[2])
    _preview(caller)
    return _next_node(caller, "menunode_modifiers")


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
        return _next_node(caller, "menunode_secondary_stats_prompt")
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
    return _next_node(caller, "menunode_secondary_stats_prompt")


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
    return _next_node(caller, "menunode_behavior")


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
        return _next_node(caller, "menunode_behavior")
    parts = string.split()
    if len(parts) != 6 or not all(p.isdigit() for p in parts):
        caller.msg("Enter six numbers separated by spaces.")
        return "menunode_stats"
    caller.ndb.buildnpc["primary_stats"] = {
        stat: int(val) for stat, val in zip(stats, parts)
    }
    _preview(caller)
    return _next_node(caller, "menunode_behavior")


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
    return _next_node(caller, "menunode_skills")


def menunode_skills(caller, raw_string="", **kwargs):
    skills = caller.ndb.buildnpc.get("skills", {})
    npc_type = caller.ndb.buildnpc.get("npc_type", NPCType.BASE)
    suggested = ", ".join(get_skills_for_class(npc_type))
    text = "|wEdit Skills|n\n"
    if skills:
        for name, chance in skills.items():
            text += f" - {name} ({chance}%)\n"
    else:
        text += "None\n"
    text += f"Suggested for {npc_type}: {suggested}\n"
    text += "Commands:\n  add <name> [chance]\n  remove <name>\n  done - finish\n  back - previous step"
    options = add_back_skip({"key": "_default", "goto": _edit_skills}, _edit_skills)
    return with_summary(caller, text), options


def _set_skills(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_behavior"
    table = caller.ndb.buildnpc.setdefault("skills", {})
    if not string or string.lower() in ("skip", "done", "finish"):
        return _next_node(caller, "menunode_spells")
    if string.lower().startswith("add "):
        parts = string[4:].split()
        if not parts:
            caller.msg("Usage: add <name> [chance]")
            return "menunode_skills"
        name = parts[0]
        chance = 100
        if len(parts) > 1:
            if not parts[1].isdigit():
                caller.msg("Chance must be a number.")
                return "menunode_skills"
            chance = int(parts[1])
        table[name] = chance
        caller.msg(f"Added {name} ({chance}%).")
        return "menunode_skills"
    if string.lower().startswith("remove "):
        name = string[7:].strip()
        if table.pop(name, None) is not None:
            caller.msg(f"Removed {name}.")
        else:
            caller.msg("Entry not found.")
        return "menunode_skills"
    caller.msg("Unknown command.")
    return "menunode_skills"


def menunode_spells(caller, raw_string="", **kwargs):
    spells = caller.ndb.buildnpc.get("spells", {})
    text = "|wEdit Spells|n\n"
    if spells:
        for name, chance in spells.items():
            text += f" - {name} ({chance}%)\n"
    else:
        text += "None\n"
    text += "Commands:\n  add <name> [chance]\n  remove <name>\n  done - finish\n  back - previous step"
    options = add_back_skip({"key": "_default", "goto": _edit_spells}, _edit_spells)
    return with_summary(caller, text), options


def _set_spells(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_skills"
    table = caller.ndb.buildnpc.setdefault("spells", {})
    if not string or string.lower() in ("skip", "done", "finish"):
        return _next_node(caller, "menunode_ai")
    if string.lower().startswith("add "):
        parts = string[4:].split()
        if not parts:
            caller.msg("Usage: add <name> [chance]")
            return "menunode_spells"
        name = parts[0]
        chance = 100
        if len(parts) > 1:
            if not parts[1].isdigit():
                caller.msg("Chance must be a number.")
                return "menunode_spells"
            chance = int(parts[1])
        table[name] = chance
        caller.msg(f"Added {name} ({chance}%).")
        return "menunode_spells"
    if string.lower().startswith("remove "):
        name = string[7:].strip()
        if table.pop(name, None) is not None:
            caller.msg(f"Removed {name}.")
        else:
            caller.msg("Entry not found.")
        return "menunode_spells"
    caller.msg("Unknown command.")
    return "menunode_spells"


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
        return _next_node(caller, "menunode_actflags")
    return _next_node(caller, "menunode_triggers")


def menunode_actflags(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("actflags", [])
    flags = ", ".join(a.value for a in ACTFLAGS)
    text = "|wAct Flags|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += f"\nAvailable: {flags}"
    text += "\nExample: |wsentinel wander aggressive assist call_for_help|n"
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
    return _next_node(caller, "menunode_affects")


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
    return _next_node(caller, "menunode_resists")


def menunode_resists(caller, raw_string="", **kwargs):
    default = caller.ndb.buildnpc.get("resistances", [])
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
        val = caller.ndb.buildnpc.get("resistances", [])
    else:
        try:
            val = [f.value for f in parse_flag_list(string, RIS_TYPES)]
        except Exception:
            caller.msg("Invalid type.")
            return "menunode_resists"
    caller.ndb.buildnpc["resistances"] = val
    return _next_node(caller, "menunode_bodyparts")


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
    return _next_node(caller, "menunode_attack")


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
    return _next_node(caller, "menunode_defense")


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
    return _next_node(caller, "menunode_languages")


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
    return _next_node(caller, "menunode_script")


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
    return _next_node(caller, "menunode_triggers")


def menunode_triggers(caller, raw_string="", **kwargs):
    """Main trigger menu."""
    text = "|wTrigger Menu|n"
    options = [
        {"desc": "Add trigger", "goto": "menunode_trigger_add"},
        {"desc": "Delete trigger", "goto": "menunode_trigger_delete"},
        {"desc": "List triggers", "goto": "menunode_trigger_list"},
        {"desc": "Finish", "goto": "menunode_review"},
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
    if event.lower() in ("back", "skip"):
        return "menunode_trigger_add"
    if not event:
        caller.msg("Enter a valid event name.")
        return "menunode_trigger_custom"
    return _set_trigger_event(caller, None, event=event)


def _set_trigger_event(caller, raw_string, event=None, **kwargs):
    caller.ndb.trigger_event = event
    return _next_node(caller, "menunode_trigger_match")


def menunode_trigger_match(caller, raw_string="", **kwargs):
    text = "|wEnter match text (blank for none)|n"
    options = add_back_skip(
        {"key": "_default", "goto": _set_trigger_match}, _set_trigger_match
    )
    return with_summary(caller, text), options


def _set_trigger_match(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() in ("back", "skip"):
        return "menunode_trigger_add"
    caller.ndb.trigger_match = string
    return _next_node(caller, "menunode_trigger_react")


def menunode_trigger_react(caller, raw_string="", **kwargs):
    text = "|wEnter reaction command(s) (comma or semicolon separated)|n"
    options = add_back_skip({"key": "_default", "goto": _save_trigger}, _save_trigger)
    return with_summary(caller, text), options


def _save_trigger(caller, raw_string, **kwargs):
    reaction = raw_string.strip()
    if reaction.lower() in ("back", "skip"):
        caller.ndb.trigger_event = None
        caller.ndb.trigger_match = None
        return "menunode_trigger_match"

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
    return _next_node(caller, "menunode_triggers")


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
    return _next_node(caller, "menunode_triggers")


def menunode_review(caller, raw_string="", **kwargs):
    """Display a summary of the build and offer navigation options."""

    data = caller.ndb.buildnpc or {}
    text = format_mob_summary(data)
    text += "\n|wReview the NPC and choose a section to edit or continue.|n"

    options = [{"desc": "Continue", "goto": "menunode_finalize"}]
    for label, node in REVIEW_SECTIONS:
        options.append({"desc": label, "goto": (_goto_section, {"node": node})})

    return text, options


def menunode_finalize(caller, raw_string="", **kwargs):
    """Offer final options before creating the NPC."""

    text = "|wFinalize NPC Creation|n"
    options = [
        {
            "key": "1",
            "desc": "Yes & Save Prototype",
            "goto": (_create_npc, {"register": True}),
        },
        {
            "key": "2",
            "desc": "Yes (Don't Save)",
            "goto": (_create_npc, {"register": False}),
        },
        {"key": "3", "desc": "Preview Prototype", "goto": "menunode_preview_proto"},
        {"key": "4", "desc": "Edit Something", "goto": "menunode_review"},
        {"key": "5", "desc": "Undo Changes", "goto": _undo_changes},
        {"key": "6", "desc": "Cancel", "goto": _cancel},
    ]

    return text, options


def menunode_preview_proto(caller, raw_string="", **kwargs):
    """Display raw prototype data."""
    data = getattr(caller.ndb, "buildnpc", {})
    import json

    text = json.dumps(data, indent=4)
    options = [{"desc": "Back", "goto": "menunode_finalize"}]
    return text, options


def _undo_changes(caller, raw_string="", **kwargs):
    """Revert builder data to the original snapshot."""
    from copy import deepcopy

    orig = getattr(caller.ndb, "buildnpc_orig", None)
    if orig:
        caller.ndb.buildnpc = deepcopy(orig)
        caller.msg("Changes reverted.")
    else:
        caller.msg("Nothing to undo.")
    return "menunode_review"


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
        "npc_type": "menunode_npc_type",
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
