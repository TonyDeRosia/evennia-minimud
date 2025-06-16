from evennia.utils.evmenu import EvMenu
from world.mob_constants import (
    NPC_RACES,
    NPC_GENDERS,
    ACTFLAGS,
    AFFECTED_BY,
    LANGUAGES,
    RIS_TYPES,
    ATTACK_TYPES,
    DEFENSE_TYPES,
    parse_flag_list,
)
from utils.mob_proto import register_prototype, get_prototype
from utils.vnum_registry import validate_vnum, register_vnum
from world.templates.mob_templates import get_template
from .command import Command

VALID_STATS = {"STR", "CON", "DEX", "INT", "WIS", "LUCK"}


def _summary(caller) -> str:
    proto = caller.ndb.mob_proto or {}
    vnum = caller.ndb.mob_vnum
    lines = [f"|wEditing mob {vnum}|n"]
    if key := proto.get("key"):
        lines.append(f"Key: {key}")
    if sd := proto.get("desc"):
        lines.append(f"Shortdesc: {sd}")
    if ld := proto.get("long_desc"):
        lines.append(f"Longdesc: {ld}")
    if lvl := proto.get("level"):
        lines.append(f"Level: {lvl}")
    if race := proto.get("race"):
        lines.append(f"Race: {race}")
    skills = proto.get("skills") or {}
    if skills:
        parts = ", ".join(f"{k}({v}%)" for k, v in skills.items())
        lines.append(f"Skills: {parts}")
    spells = proto.get("spells") or {}
    if spells:
        parts = ", ".join(f"{k}({v}%)" for k, v in spells.items())
        lines.append(f"Spells: {parts}")
    return "\n".join(lines)


def _with_summary(caller, text: str) -> str:
    return f"{_summary(caller)}\n\n{text}"


def _parse_stats(text: str) -> dict:
    tokens = text.replace(",", " ").split()
    if len(tokens) % 2 != 0:
        raise ValueError("Enter stat/value pairs like 'STR 10 DEX 8'")
    stats = {}
    it = iter(tokens)
    for stat in it:
        key = stat.upper()
        if key not in VALID_STATS:
            raise ValueError(stat)
        try:
            val = int(next(it))
        except (StopIteration, ValueError):
            raise ValueError(stat)
        stats[key] = val
    return stats


def _parse_flags(text: str, enum_cls) -> list[str]:
    flags = []
    for part in text.split():
        try:
            flags.append(enum_cls.from_str(part).value)
        except ValueError:
            raise ValueError(part)
    return flags


# ----------------------------------------------------------------------
# Menu nodes
# ----------------------------------------------------------------------


def menunode_main(caller, raw_string="", **kwargs):
    text = "Choose an option:"
    options = [
        {"desc": "Edit key", "goto": "menunode_key"},
        {"desc": "Edit shortdesc", "goto": "menunode_short"},
        {"desc": "Edit longdesc", "goto": "menunode_long"},
        {"desc": "Edit level", "goto": "menunode_level"},
        {"desc": "Edit race", "goto": "menunode_race"},
        {"desc": "Edit gender", "goto": "menunode_gender"},
        {"desc": "Edit stats", "goto": "menunode_stats"},
        {"desc": "Edit defenses", "goto": "menunode_defenses"},
        {"desc": "Edit resists", "goto": "menunode_resists"},
        {"desc": "Edit languages", "goto": "menunode_languages"},
        {"desc": "Edit loot", "goto": "menunode_loot"},
        {"desc": "Edit inventory", "goto": "menunode_inventory"},
        {"desc": "Edit equipment", "goto": "menunode_equipment"},
        {"desc": "Edit skills", "goto": "menunode_skills"},
        {"desc": "Edit spells", "goto": "menunode_spells"},
        {"desc": "Edit actflags", "goto": "menunode_actflags"},
        {"desc": "Edit affects", "goto": "menunode_affects"},
        {"desc": "Edit attacks", "goto": "menunode_attacks"},
        {"desc": "Edit AI flags", "goto": "menunode_ai_flags"},
        {"desc": "Cancel", "goto": "menunode_cancel"},
        {"desc": "Save & quit", "goto": "menunode_done"},
    ]
    return _with_summary(caller, text), options


def menunode_key(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("key", "")
    text = f"|wMob key|n [current: {default}]"
    options = {"key": "_default", "goto": _set_key}
    return text, options


def _set_key(caller, raw_string, **kwargs):
    if raw_string.strip():
        caller.ndb.mob_proto["key"] = raw_string.strip()
    return "menunode_main"


def menunode_short(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("desc", "")
    text = f"|wShort description|n [current: {default}]"
    options = {"key": "_default", "goto": _set_short}
    return text, options


def _set_short(caller, raw_string, **kwargs):
    caller.ndb.mob_proto["desc"] = raw_string.strip()
    return "menunode_main"


def menunode_long(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("long_desc", "")
    text = f"|wLong description|n [current: {default}]"
    options = {"key": "_default", "goto": _set_long}
    return text, options


def _set_long(caller, raw_string, **kwargs):
    caller.ndb.mob_proto["long_desc"] = raw_string.strip()
    return "menunode_main"


def menunode_level(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("level", 1)
    text = f"|wLevel|n [current: {default}]"
    options = {"key": "_default", "goto": _set_level}
    return text, options


def _set_level(caller, raw_string, **kwargs):
    if not raw_string.strip().isdigit():
        caller.msg("Level must be numeric.")
        return "menunode_level"
    val = int(raw_string.strip())
    caller.ndb.mob_proto["level"] = val
    stats = {
        "STR": 5 + val // 2,
        "CON": 5 + val // 2,
        "DEX": 5 + val // 3,
        "INT": 3 + val // 3,
        "WIS": 3 + val // 3,
        "LUCK": 5 + val // 4,
        "PER": 5 + val // 4,
    }
    caller.ndb.mob_proto["primary_stats"] = stats
    parts = "  ".join(f"{k} {v}" for k, v in stats.items())
    caller.msg(
        f"Level set to {val}. Primary stats auto-scaled:\n{parts}\n(You may override these manually in 'Edit stats'.)"
    )
    return "menunode_main"


def menunode_race(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("race", "")
    valid = ", ".join(r.value for r in NPC_RACES)
    text = f"|wRace|n [current: {current}]\nValid: {valid}"
    options = {"key": "_default", "goto": _set_race}
    return text, options


def _set_race(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if not val:
        return "menunode_main"
    try:
        caller.ndb.mob_proto["race"] = NPC_RACES.from_str(val).value
    except ValueError:
        caller.msg("Invalid race.")
        return "menunode_race"
    return "menunode_main"


def menunode_gender(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("gender", "")
    valid = ", ".join(g.value for g in NPC_GENDERS)
    text = f"|wGender|n [current: {current}]\nValid: {valid}"
    options = {"key": "_default", "goto": _set_gender}
    return text, options


def _set_gender(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if not val:
        return "menunode_main"
    try:
        caller.ndb.mob_proto["gender"] = NPC_GENDERS.from_str(val).value
    except ValueError:
        caller.msg("Invalid gender.")
        return "menunode_gender"
    return "menunode_main"


def menunode_stats(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("primary_stats", {})
    curstr = ", ".join(f"{k} {v}" for k, v in current.items())
    text = f"|wPrimary stats|n [current: {curstr}]"
    options = {"key": "_default", "goto": _set_stats}
    return text, options


def _set_stats(caller, raw_string, **kwargs):
    try:
        stats = _parse_stats(raw_string)
    except ValueError:
        caller.msg("Enter stat/value pairs like 'STR 10 DEX 8'")
        return "menunode_stats"
    caller.ndb.mob_proto["primary_stats"] = stats
    return "menunode_main"


def menunode_actflags(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("actflags", [])
    valid = " ".join(f.value for f in ACTFLAGS)
    text = f"|wAct flags|n [current: {' '.join(current)}]\nValid: {valid}"
    options = {"key": "_default", "goto": _set_actflags}
    return text, options


def _set_actflags(caller, raw_string, **kwargs):
    try:
        flags = _parse_flags(raw_string, ACTFLAGS)
    except ValueError as err:
        caller.msg(f"Invalid flag: {err}")
        return "menunode_actflags"
    caller.ndb.mob_proto["actflags"] = flags
    return "menunode_main"


def menunode_affects(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("affected_by", [])
    valid = " ".join(f.value for f in AFFECTED_BY)
    text = f"|wAffects|n [current: {' '.join(current)}]\nValid: {valid}"
    options = {"key": "_default", "goto": _set_affects}
    return text, options


def _set_affects(caller, raw_string, **kwargs):
    try:
        flags = _parse_flags(raw_string, AFFECTED_BY)
    except ValueError as err:
        caller.msg(f"Invalid affect: {err}")
        return "menunode_affects"
    caller.ndb.mob_proto["affected_by"] = flags
    return "menunode_main"


def menunode_attacks(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("attack_types", [])
    valid = " ".join(f.value for f in ATTACK_TYPES)
    text = f"|wAttacks|n [current: {' '.join(current)}]\nValid: {valid}"
    options = {"key": "_default", "goto": _set_attacks}
    return text, options


def _set_attacks(caller, raw_string, **kwargs):
    try:
        flags = _parse_flags(raw_string, ATTACK_TYPES)
    except ValueError as err:
        caller.msg(f"Invalid attack: {err}")
        return "menunode_attacks"
    caller.ndb.mob_proto["attack_types"] = flags
    return "menunode_main"


def menunode_defenses(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("defense_types", [])
    valid = " ".join(f.value for f in DEFENSE_TYPES)
    text = f"|wDefenses|n [current: {' '.join(current)}]\nValid: {valid}"
    options = {"key": "_default", "goto": _set_defenses}
    return text, options


def _set_defenses(caller, raw_string, **kwargs):
    try:
        flags = _parse_flags(raw_string, DEFENSE_TYPES)
    except ValueError as err:
        caller.msg(f"Invalid defense: {err}")
        return "menunode_defenses"
    caller.ndb.mob_proto["defense_types"] = flags
    return "menunode_main"


def menunode_resists(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("resistances", [])
    valid = " ".join(f.value for f in RIS_TYPES)
    text = f"|wResists|n [current: {' '.join(current)}]\nValid: {valid}"
    options = {"key": "_default", "goto": _set_resists}
    return text, options


def _set_resists(caller, raw_string, **kwargs):
    try:
        flags = _parse_flags(raw_string, RIS_TYPES)
    except ValueError as err:
        caller.msg(f"Invalid resist: {err}")
        return "menunode_resists"
    caller.ndb.mob_proto["resistances"] = flags
    return "menunode_main"


def menunode_languages(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("languages", [])
    valid = " ".join(f.value for f in LANGUAGES)
    text = f"|wLanguages|n [current: {' '.join(current)}]\nValid: {valid}"
    options = {"key": "_default", "goto": _set_languages}
    return text, options


def _set_languages(caller, raw_string, **kwargs):
    try:
        flags = _parse_flags(raw_string, LANGUAGES)
    except ValueError as err:
        caller.msg(f"Invalid language: {err}")
        return "menunode_languages"
    caller.ndb.mob_proto["languages"] = flags
    return "menunode_main"


def menunode_loot(caller, raw_string="", **kwargs):
    """Menu for editing loot table entries."""
    loot = caller.ndb.mob_proto.get("loot_table", [])
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
        "Commands:\n  add <proto> [chance] [amount] [guaranteed]\n  remove <proto>\n  "
        "done - return\n  back - return\nExample: |wadd 100001 50|n, |wadd gold 100 5|n"
    )
    options = {"key": "_default", "goto": _edit_loot}
    return _with_summary(caller, text), options


def _edit_loot(caller, raw_string, **kwargs):
    from utils.currency import COIN_VALUES
    from utils.prototype_manager import load_prototype
    from utils import vnum_registry

    string = raw_string.strip()
    table = caller.ndb.mob_proto.setdefault("loot_table", [])
    if string.lower() in ("back", "done", "finish", ""):
        return "menunode_main"
    if string.lower().startswith("add "):
        parts = string[4:].split()
        if not parts:
            caller.msg("Usage: add <proto> [chance] [amount] [guaranteed]")
            return "menunode_loot"
        proto = parts[0]
        if proto.isdigit():
            vnum = int(proto)
            if (
                not vnum_registry.VNUM_RANGES["object"][0]
                <= vnum
                <= vnum_registry.VNUM_RANGES["object"][1]
            ):
                caller.msg("Invalid object VNUM.")
                return "menunode_loot"
            if not load_prototype("object", vnum):
                caller.msg("Unknown object VNUM.")
                return "menunode_loot"
            proto = vnum
        chance = 100
        amount = 1
        guaranteed = None
        if len(parts) > 1:
            if not parts[1].isdigit():
                caller.msg("Chance must be a number.")
                return "menunode_loot"
            chance = int(parts[1])
        if isinstance(proto, str) and proto.lower() in COIN_VALUES and len(parts) > 2:
            if not parts[2].isdigit():
                caller.msg("Amount must be a number.")
                return "menunode_loot"
            amount = int(parts[2])
            if len(parts) > 3:
                if not parts[3].isdigit():
                    caller.msg("Guaranteed count must be a number.")
                    return "menunode_loot"
                guaranteed = int(parts[3])
        elif len(parts) > 2:
            if not parts[2].isdigit():
                caller.msg("Guaranteed count must be a number.")
                return "menunode_loot"
            guaranteed = int(parts[2])
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
        return "menunode_loot"
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
        return "menunode_loot"
    caller.msg("Unknown command.")
    return "menunode_loot"


def menunode_inventory(caller, raw_string="", **kwargs):
    """Menu for editing starting inventory VNUMs."""
    items = caller.ndb.mob_proto.get("inventory", [])
    text = "|wEdit Inventory|n\n"
    if items:
        for vnum in items:
            text += f" - {vnum}\n"
    else:
        text += "None\n"
    text += "Commands:\n  add <vnum>\n  remove <vnum>\n  done/back - return"
    options = {"key": "_default", "goto": _edit_inventory}
    return _with_summary(caller, text), options


def _edit_inventory(caller, raw_string, **kwargs):
    from utils.prototype_manager import load_prototype
    from utils import vnum_registry

    string = raw_string.strip()
    table = caller.ndb.mob_proto.setdefault("inventory", [])
    if string.lower() in ("back", "done", "finish", ""):
        return "menunode_main"
    if string.lower().startswith("add "):
        vnum_str = string[4:].strip()
        if not vnum_str.isdigit():
            caller.msg("Usage: add <vnum>")
            return "menunode_inventory"
        vnum = int(vnum_str)
        if (
            not vnum_registry.VNUM_RANGES["object"][0]
            <= vnum
            <= vnum_registry.VNUM_RANGES["object"][1]
        ):
            caller.msg("Invalid object VNUM.")
            return "menunode_inventory"
        if not load_prototype("object", vnum):
            caller.msg("Unknown object VNUM.")
            return "menunode_inventory"
        if vnum not in table:
            table.append(vnum)
            caller.msg(f"Added {vnum}.")
        else:
            caller.msg("VNUM already present.")
        return "menunode_inventory"
    if string.lower().startswith("remove "):
        vnum_str = string[7:].strip()
        if not vnum_str.isdigit():
            caller.msg("Usage: remove <vnum>")
            return "menunode_inventory"
        vnum = int(vnum_str)
        if vnum in table:
            table.remove(vnum)
            caller.msg(f"Removed {vnum}.")
        else:
            caller.msg("Entry not found.")
        return "menunode_inventory"
    caller.msg("Unknown command.")
    return "menunode_inventory"


def menunode_equipment(caller, raw_string="", **kwargs):
    """Menu for editing equipped item VNUMs."""
    items = caller.ndb.mob_proto.get("equipment", [])
    text = "|wEdit Equipment|n\n"
    if items:
        for vnum in items:
            text += f" - {vnum}\n"
    else:
        text += "None\n"
    text += "Commands:\n  add <vnum>\n  remove <vnum>\n  done/back - return"
    options = {"key": "_default", "goto": _edit_equipment}
    return _with_summary(caller, text), options


def _edit_equipment(caller, raw_string, **kwargs):
    from utils.prototype_manager import load_prototype
    from utils import vnum_registry

    string = raw_string.strip()
    table = caller.ndb.mob_proto.setdefault("equipment", [])
    if string.lower() in ("back", "done", "finish", ""):
        return "menunode_main"
    if string.lower().startswith("add "):
        vnum_str = string[4:].strip()
        if not vnum_str.isdigit():
            caller.msg("Usage: add <vnum>")
            return "menunode_equipment"
        vnum = int(vnum_str)
        if (
            not vnum_registry.VNUM_RANGES["object"][0]
            <= vnum
            <= vnum_registry.VNUM_RANGES["object"][1]
        ):
            caller.msg("Invalid object VNUM.")
            return "menunode_equipment"
        if not load_prototype("object", vnum):
            caller.msg("Unknown object VNUM.")
            return "menunode_equipment"
        if vnum not in table:
            table.append(vnum)
            caller.msg(f"Added {vnum}.")
        else:
            caller.msg("VNUM already present.")
        return "menunode_equipment"
    if string.lower().startswith("remove "):
        vnum_str = string[7:].strip()
        if not vnum_str.isdigit():
            caller.msg("Usage: remove <vnum>")
            return "menunode_equipment"
        vnum = int(vnum_str)
        if vnum in table:
            table.remove(vnum)
            caller.msg(f"Removed {vnum}.")
        else:
            caller.msg("Entry not found.")
        return "menunode_equipment"
    caller.msg("Unknown command.")
    return "menunode_equipment"


def menunode_skills(caller, raw_string="", **kwargs):
    """Menu for editing skill chances."""
    skills = caller.ndb.mob_proto.get("skills", {})
    text = "|wEdit Skills|n\n"
    if skills:
        for name, chance in skills.items():
            text += f" - {name} ({chance}%)\n"
    else:
        text += "None\n"
    text += "Commands:\n  add <name> [chance]\n  remove <name>\n  done/back - return"
    options = {"key": "_default", "goto": _edit_skills}
    return _with_summary(caller, text), options


def _edit_skills(caller, raw_string, **kwargs):
    string = raw_string.strip()
    table = caller.ndb.mob_proto.setdefault("skills", {})
    if string.lower() in ("back", "done", "finish", ""):
        return "menunode_main"
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
    """Menu for editing spell chances."""
    spells = caller.ndb.mob_proto.get("spells", {})
    text = "|wEdit Spells|n\n"
    if spells:
        for name, chance in spells.items():
            text += f" - {name} ({chance}%)\n"
    else:
        text += "None\n"
    text += "Commands:\n  add <name> [chance]\n  remove <name>\n  done/back - return"
    options = {"key": "_default", "goto": _edit_spells}
    return _with_summary(caller, text), options


def _edit_spells(caller, raw_string, **kwargs):
    string = raw_string.strip()
    table = caller.ndb.mob_proto.setdefault("spells", {})
    if string.lower() in ("back", "done", "finish", ""):
        return "menunode_main"
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


def menunode_ai_flags(caller, raw_string="", **kwargs):
    """Placeholder for AI flag editing."""
    caller.msg("AI flag editing not yet implemented.")
    return "menunode_main"


def menunode_done(caller, raw_string="", **kwargs):
    proto = caller.ndb.mob_proto or {}
    vnum = caller.ndb.mob_vnum
    try:
        register_prototype(proto, vnum=vnum)
    except ValueError as err:
        caller.msg(str(err))
        return "menunode_main"
    caller.msg(f"Mob prototype {vnum} saved.")
    caller.ndb.mob_proto = None
    caller.ndb.mob_vnum = None
    return None


def menunode_cancel(caller, raw_string="", **kwargs):
    caller.msg("Editing cancelled.")
    caller.ndb.mob_proto = None
    caller.ndb.mob_vnum = None
    return None


class CmdMEdit(Command):
    """Edit or create an NPC prototype using a ROM-style menu."""

    key = "medit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"
    help_text = (
        "Edit or create an NPC prototype.\n\n"
        "Usage:\n    medit <vnum>\n    medit create <vnum>\n\n"
        "Inventory and equipment entries accept object VNUMs."
    )

    def func(self):
        caller = self.caller
        args = self.args.strip()
        if not args:
            caller.msg("Usage: medit <vnum> | medit create <vnum>")
            return
        parts = args.split(None, 1)
        sub = parts[0].lower()
        if sub == "create":
            if len(parts) != 2 or not parts[1].isdigit():
                caller.msg("Usage: medit create <vnum>")
                return
            vnum = int(parts[1])
            if get_prototype(vnum) is not None or not validate_vnum(vnum, "npc"):
                caller.msg("Invalid or already used VNUM.")
                return
            register_vnum(vnum)
            proto = get_template("warrior") or {}
            proto.setdefault("key", f"mob_{vnum}")
            proto.setdefault("level", 1)
        else:
            if not sub.isdigit():
                caller.msg("Usage: medit <vnum> | medit create <vnum>")
                return
            vnum = int(sub)
            proto = get_prototype(sub)
            if not proto:
                caller.msg(f"Prototype {sub} not found.")
                return
        proto["vnum"] = vnum
        caller.ndb.mob_vnum = vnum
        caller.ndb.mob_proto = dict(proto)
        EvMenu(caller, "commands.rom_mob_editor", startnode="menunode_main")
