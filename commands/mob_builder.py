# coding: utf-8
"""Simple mob building workflow using EvMenu."""

from evennia.utils.evmenu import EvMenu
from evennia.prototypes import spawner
from typeclasses.npcs import NPC

from world import prototypes
from world.mob_constants import (
    NPC_CLASSES,
    NPC_RACES,
    ACTFLAGS,
    AFFECTED_BY,
    LANGUAGES,
    BODYPARTS,
    RIS_TYPES,
    ATTACK_TYPES,
    DEFENSE_TYPES,
    parse_flag_list,
)

from .command import Command


# ------------------------------------------------------------
# Helper utils
# ------------------------------------------------------------

def _parse_enum(value, enum_cls):
    try:
        return enum_cls.from_str(value).value
    except Exception:
        raise ValueError(value)


def _parse_enum_list(text, enum_cls):
    if not text:
        return []
    vals = []
    for part in text.split():
        vals.append(_parse_enum(part, enum_cls))
    return vals


# ------------------------------------------------------------
# Menu nodes
# ------------------------------------------------------------

def menunode_key(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("key", "") if caller.ndb.mob_build else ""
    text = "|wEnter mob key|n"
    if default:
        text += f" [default: {default}]"
    options = {"key": "_default", "goto": _set_key}
    return text, options


def _set_key(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if val.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("key", "")
    if not caller.ndb.mob_build:
        caller.ndb.mob_build = {}
    caller.ndb.mob_build["key"] = val
    return "menunode_desc"


def menunode_desc(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("desc", "")
    text = "|wShort description|n"
    if default:
        text += f" [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_desc}
    return text, options


def _set_desc(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_key"
    if string.lower() in ("skip", ""):
        string = caller.ndb.mob_build.get("desc", "")
    caller.ndb.mob_build["desc"] = string
    return "menunode_level"


def menunode_level(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("level", 1)
    text = f"|wLevel|n [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_level}
    return text, options


def _set_level(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_desc"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("level", 1)
    else:
        try:
            val = int(string)
        except ValueError:
            caller.msg("Enter a number.")
            return "menunode_level"
    caller.ndb.mob_build["level"] = val
    return "menunode_class"


def menunode_class(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("npc_class", "warrior")
    text = f"|wClass|n ({'/'.join(m.value for m in NPC_CLASSES)})"
    if default:
        text += f" [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_class}
    return text, options


def _set_class(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_level"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("npc_class", "warrior")
    else:
        try:
            val = _parse_enum(string, NPC_CLASSES)
        except ValueError:
            caller.msg("Invalid class.")
            return "menunode_class"
    caller.ndb.mob_build["npc_class"] = val
    return "menunode_race"


def menunode_race(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("race", "human")
    text = f"|wRace|n ({'/'.join(r.value for r in NPC_RACES)})"
    if default:
        text += f" [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_race}
    return text, options


def _set_race(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_class"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("race", "human")
    else:
        try:
            val = _parse_enum(string, NPC_RACES)
        except ValueError:
            caller.msg("Invalid race.")
            return "menunode_race"
    caller.ndb.mob_build["race"] = val
    return "menunode_sex"


def menunode_sex(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("sex", "unspecified")
    text = "|wSex|n (male/female/neutral)"
    if default:
        text += f" [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_sex}
    return text, options


def _set_sex(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    if string == "back":
        return "menunode_race"
    if string in ("skip", ""):
        val = caller.ndb.mob_build.get("sex", "unspecified")
    else:
        val = string
    caller.ndb.mob_build["sex"] = val
    return "menunode_hp"


def menunode_hp(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("hp", 0)
    text = f"|wHP|n [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_hp}
    return text, options


def _set_hp(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_sex"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("hp", 0)
    else:
        try:
            val = int(string)
        except ValueError:
            caller.msg("Enter a number.")
            return "menunode_hp"
    caller.ndb.mob_build["hp"] = val
    return "menunode_damage"


def menunode_damage(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("damage", 0)
    text = f"|wDamage|n [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_damage}
    return text, options


def _set_damage(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_hp"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("damage", 0)
    else:
        try:
            val = int(string)
        except ValueError:
            caller.msg("Enter a number.")
            return "menunode_damage"
    caller.ndb.mob_build["damage"] = val
    return "menunode_armor"


def menunode_armor(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("armor", 0)
    text = f"|wArmor|n [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_armor}
    return text, options


def _set_armor(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_damage"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("armor", 0)
    else:
        try:
            val = int(string)
        except ValueError:
            caller.msg("Enter a number.")
            return "menunode_armor"
    caller.ndb.mob_build["armor"] = val
    return "menunode_align"


def menunode_align(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("align", 0)
    text = f"|wAlignment|n [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_align}
    return text, options


def _set_align(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_armor"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("align", 0)
    else:
        try:
            val = int(string)
        except ValueError:
            caller.msg("Enter a number.")
            return "menunode_align"
    caller.ndb.mob_build["align"] = val
    return "menunode_flags"


def menunode_flags(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("actflags", [])
    text = "|wAct Flags|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_flags}
    return text, options


def _set_flags(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_align"
    if string.lower() in ("skip", ""):
        flags = caller.ndb.mob_build.get("actflags", [])
    else:
        try:
            flags = _parse_enum_list(string, ACTFLAGS)
        except ValueError:
            caller.msg("Invalid flag.")
            return "menunode_flags"
    caller.ndb.mob_build["actflags"] = flags
    return "menunode_affects"


def menunode_affects(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("affected_by", [])
    text = "|wAffects|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_affects}
    return text, options


def _set_affects(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_flags"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("affected_by", [])
    else:
        try:
            val = _parse_enum_list(string, AFFECTED_BY)
        except ValueError:
            caller.msg("Invalid affect flag.")
            return "menunode_affects"
    caller.ndb.mob_build["affected_by"] = val
    return "menunode_resists"


def menunode_resists(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("ris", [])
    text = "|wResists/Immunities|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_resists}
    return text, options


def _set_resists(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_affects"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("ris", [])
    else:
        try:
            val = _parse_enum_list(string, RIS_TYPES)
        except ValueError:
            caller.msg("Invalid type.")
            return "menunode_resists"
    caller.ndb.mob_build["ris"] = val
    return "menunode_bodyparts"


def menunode_bodyparts(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("bodyparts", [])
    text = "|wBodyparts|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_bodyparts}
    return text, options


def _set_bodyparts(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_resists"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("bodyparts", [])
    else:
        try:
            val = _parse_enum_list(string, BODYPARTS)
        except ValueError:
            caller.msg("Invalid bodypart.")
            return "menunode_bodyparts"
    caller.ndb.mob_build["bodyparts"] = val
    return "menunode_attack"


def menunode_attack(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("attack_types", [])
    text = "|wAttack types|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_attack}
    return text, options


def _set_attack(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_bodyparts"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("attack_types", [])
    else:
        try:
            val = _parse_enum_list(string, ATTACK_TYPES)
        except ValueError:
            caller.msg("Invalid attack type.")
            return "menunode_attack"
    caller.ndb.mob_build["attack_types"] = val
    return "menunode_defense"


def menunode_defense(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("defense_types", [])
    text = "|wDefense types|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_defense}
    return text, options


def _set_defense(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_attack"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("defense_types", [])
    else:
        try:
            val = _parse_enum_list(string, DEFENSE_TYPES)
        except ValueError:
            caller.msg("Invalid defense type.")
            return "menunode_defense"
    caller.ndb.mob_build["defense_types"] = val
    return "menunode_languages"


def menunode_languages(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("languages", [])
    text = "|wLanguages|n (space separated)"
    if default:
        text += f" [default: {' '.join(default)}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_languages}
    return text, options


def _set_languages(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_defense"
    if string.lower() in ("skip", ""):
        val = caller.ndb.mob_build.get("languages", [])
    else:
        try:
            val = _parse_enum_list(string, LANGUAGES)
        except ValueError:
            caller.msg("Invalid language.")
            return "menunode_languages"
    caller.ndb.mob_build["languages"] = val
    return "menunode_role"


def menunode_role(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("role", "")
    text = "|wSpecial role|n (merchant/questgiver/trainer/guard/banker/none)"
    if default:
        text += f" [default: {default}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_role}
    return text, options


def _set_role(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    if string == "back":
        return "menunode_languages"
    if string in ("skip", ""):
        val = caller.ndb.mob_build.get("role", "")
    else:
        val = string
    caller.ndb.mob_build["role"] = val
    if val in ("merchant", "shop", "repair"):
        return "menunode_shop"
    return "menunode_confirm"


def menunode_shop(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_build.get("shop", {})
    text = "|wShop config|n as 'buy sell hours'"
    if default:
        text += f" [default: {default.get('buy', 100)} {default.get('sell', 100)} {default.get('hours', '0-24')}]"
    text += "\n(back, skip, done)"
    options = {"key": "_default", "goto": _set_shop}
    return text, options


def _set_shop(caller, raw_string, **kwargs):
    string = raw_string.strip()
    if string.lower() == "back":
        return "menunode_role"
    if string.lower() in ("skip", ""):
        shop = caller.ndb.mob_build.get("shop", {})
    else:
        parts = string.split()
        if len(parts) != 3:
            caller.msg("Enter buy sell hours")
            return "menunode_shop"
        try:
            buy = int(parts[0])
            sell = int(parts[1])
        except ValueError:
            caller.msg("Buy and sell must be numbers")
            return "menunode_shop"
        hours = parts[2]
        shop = {"buy": buy, "sell": sell, "hours": hours}
    caller.ndb.mob_build["shop"] = shop
    return "menunode_confirm"


def menunode_confirm(caller, raw_string="", **kwargs):
    data = caller.ndb.mob_build or {}
    text = "|wConfirm prototype?|n\n"
    for k, v in data.items():
        text += f"{k}: {v}\n"
    text += "Save? (yes/no/back)"
    options = {"key": "_default", "goto": _do_confirm}
    return text, options


def _do_confirm(caller, raw_string, **kwargs):
    string = raw_string.strip().lower()
    if string == "back":
        if caller.ndb.mob_build and caller.ndb.mob_build.get("role") in (
            "merchant",
            "shop",
            "repair",
        ):
            return "menunode_shop"
        return "menunode_role"
    if string not in ("yes", "y", "done", ""):
        caller.msg("Cancelled.")
        caller.ndb.mob_build = None
        return None
    data = caller.ndb.mob_build or {}
    key = data.get("key")
    if not key:
        caller.msg("Error: key missing.")
        return None
    proto_key = f"mob_{key}"
    proto = dict(data)
    proto["typeclass"] = "typeclasses.npcs.NPC"
    prototypes.register_npc_prototype(proto_key, proto)
    caller.msg(f"Prototype {proto_key} saved.")
    caller.ndb.mob_build = None
    return None


# ------------------------------------------------------------
# Commands
# ------------------------------------------------------------

class CmdMobBuilder(Command):
    """Start the mob builder menu."""

    key = "mobbuilder"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        EvMenu(self.caller, "commands.mob_builder", startnode="menunode_key")


class CmdMSpawn(Command):
    """Spawn a mob prototype."""

    key = "@mspawn"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        key = self.args.strip()
        if not key:
            self.msg("Usage: @mspawn <prototype>")
            return
        registry = prototypes.get_npc_prototypes()
        proto = registry.get(key) or registry.get(f"mob_{key}")
        if not proto:
            self.msg("Prototype not found.")
            return
        obj = spawner.spawn(proto)[0]
        obj.move_to(self.caller.location, quiet=True)
        self.msg(f"Spawned {obj.key}.")


# simple re-export wrappers for existing commands
from .mob_builder_commands import CmdMStat as _OldMStat, CmdMList as _OldMList


class CmdMStat(_OldMStat):
    pass


class CmdMList(_OldMList):
    pass

