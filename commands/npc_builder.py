from evennia.utils import make_iter, dedent
from olc.base import OLCEditor, OLCState, OLCValidator
from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.prototypes import spawner
from utils.mob_proto import spawn_from_vnum, get_prototype
from evennia.prototypes.prototypes import PROTOTYPE_TAG_CATEGORY
from typeclasses.characters import NPC
from world.scripts.mob_db import get_mobdb
from typeclasses.npcs import (
    BaseNPC,
    MerchantNPC,
    BankerNPC,
    TrainerNPC,
    WandererNPC,
    GuildmasterNPC,
    GuildReceptionistNPC,
    QuestGiverNPC,
    CombatNPC,
    CombatTrainerNPC,
    EventNPC,
)
from utils.slots import SLOT_ORDER
from utils.menu_utils import (
    add_back_skip,
    add_back_next,
    add_back_only,
    toggle_multi_select,
    format_multi_select,
)
from world.npc_roles import (
    MerchantRole,
    BankerRole,
    TrainerRole,
    GuildmasterRole,
    GuildReceptionistRole,
    QuestGiverRole,
    CombatTrainerRole,
    EventNPCRole,
)
from world.scripts import classes
from scripts import BuilderAutosave
from utils import vnum_registry
from utils.mob_utils import generate_base_stats, mobprogs_to_triggers
from world.triggers import TriggerManager
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
    NPCType,
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

    combat_class = data.get("combat_class")
    npc_type = data.get("npc_type")
    try:
        npc_type_enum = (
            npc_type
            if isinstance(npc_type, NPCType)
            else NPCType.from_str(str(npc_type))
        )
    except ValueError:
        npc_type_enum = None
    if combat_class and npc_type_enum not in COMBATANT_TYPES:
        warnings.append("Combat class set on non-combat NPC type.")

    return warnings


class NPCValidator(OLCValidator):
    """Validator that wraps :func:`validate_prototype`."""

    def validate(self, data: dict) -> list[str]:  # type: ignore[override]
        return validate_prototype(data)


def _auto_fill_combat_stats(data: dict) -> None:
    """Populate missing combat stats if class and level are set."""
    combat_class = data.get("combat_class")
    level = data.get("level")
    if not combat_class or not level:
        return
    stats = generate_base_stats(combat_class, level)
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

# Mapping of simple keys to NPC typeclass classes
NPC_TYPE_MAP = {
    NPCType.BASE: BaseNPC,
    NPCType.MERCHANT: MerchantNPC,
    NPCType.BANKER: BankerNPC,
    NPCType.TRAINER: TrainerNPC,
    NPCType.WANDERER: WandererNPC,
    NPCType.GUILDMASTER: GuildmasterNPC,
    NPCType.GUILD_RECEPTIONIST: GuildReceptionistNPC,
    NPCType.QUESTGIVER: QuestGiverNPC,
    NPCType.COMBATANT: CombatNPC,
    NPCType.COMBAT_TRAINER: CombatTrainerNPC,
    NPCType.EVENT_NPC: EventNPC,
}

# NPC types that can participate in combat and therefore need a combat class
COMBATANT_TYPES = {NPCType.COMBATANT, NPCType.COMBAT_TRAINER}

# Mapping of role names to mixin classes
ROLE_MIXIN_MAP = {
    "merchant": MerchantRole,
    "banker": BankerRole,
    "trainer": TrainerRole,
    "guildmaster": GuildmasterRole,
    "guild_receptionist": GuildReceptionistRole,
    "questgiver": QuestGiverRole,
    "combat_trainer": CombatTrainerRole,
    "event_npc": EventNPCRole,
}


# Suggested skill lists for each NPC class
DEFAULT_SKILLS = list(SKILL_CLASSES.keys())
SKILLS_BY_CLASS = {
    "merchant": ["appraise"],
    "combat_trainer": DEFAULT_SKILLS,
    "base": DEFAULT_SKILLS,
}


def get_skills_for_class(npc_type: str) -> list[str]:
    """Return list of suggested skills for ``npc_type``."""
    return SKILLS_BY_CLASS.get(npc_type, DEFAULT_SKILLS)


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

# Mapping of review option labels to menu nodes
REVIEW_SECTIONS = [
    ("Key", "menunode_key"),
    ("Description", "menunode_desc"),
    ("Race", "menunode_race"),
    ("NPC Type", "menunode_npc_type"),
    ("Gender", "menunode_gender"),
    ("Weight", "menunode_weight"),
    ("Level", "menunode_level"),
    ("VNUM", "menunode_vnum"),
    ("Creature Type", "menunode_creature_type"),
    ("Combat Class", "menunode_combat_class"),
    ("Role Details", "menunode_role_details"),
    ("EXP Reward", "menunode_exp_reward"),
    ("Coin Drop", "menunode_coin_drop"),
    ("Loot Table", "menunode_loot_table"),
    ("Resources", "menunode_resources_prompt"),
    ("Combat Values", "menunode_combat_values"),
    ("Modifiers", "menunode_modifiers"),
    ("Primary Stats", "menunode_secondary_stats_prompt"),
    ("Behavior", "menunode_behavior"),
    ("Skills", "menunode_skills"),
    ("Spells", "menunode_spells"),
    ("AI Type", "menunode_ai"),
    ("Act Flags", "menunode_actflags"),
    ("Affects", "menunode_affects"),
    ("Resists", "menunode_resists"),
    ("Bodyparts", "menunode_bodyparts"),
    ("Attacks", "menunode_attack"),
    ("Defenses", "menunode_defense"),
    ("Languages", "menunode_languages"),
    ("Script", "menunode_script"),
    ("Triggers", "menunode_triggers"),
]


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
        """Format the given value for display."""

        if isinstance(value, dict):
            return ", ".join(f"{k}:{v}" for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value)
        return str(value)

    def add_row(table, label, key):
        """Add ``label``/``value`` row if ``value`` is not empty."""

        value = data.get(key)
        if value is None or value == "" or value == [] or value == {}:
            return
        table.add_row(label, fmt(value))

    lines = [f"|cMob Prototype:|n {data.get('key', '--')}"]

    core = []
    if "vnum" in data and data.get("vnum") is not None:
        core.append(f"|cVNUM:|n {fmt(data.get('vnum'))}")
    if data.get("npc_type"):
        core.append(f"|cNPC Archetype:|n {fmt(data.get('npc_type'))}")
    if data.get("combat_class"):
        core.append(f"|cCombat Class:|n {fmt(data.get('combat_class'))}")
    if data.get("race"):
        core.append(f"|cRace:|n {fmt(data.get('race'))}")
    if core:
        lines.append(" | ".join(core))

    basic = EvTable(border="cells")
    add_row(basic, "|cShort Desc|n", "desc")
    add_row(basic, "|cLevel|n", "level")
    add_row(basic, "|cGender|n", "gender")
    add_row(basic, "|cWeight|n", "weight")
    roles = data.get("roles") or []
    if roles:
        unique_roles = []
        for role in roles:
            if role and role not in unique_roles:
                unique_roles.append(role)
        if unique_roles:
            basic.add_row("|cRoles|n", fmt(unique_roles))
    add_row(basic, "|cCreature|n", "creature_type")
    add_row(basic, "|cGuild|n", "guild_affiliation")
    lines.append("\n|cBasic Info|n")
    lines.append(str(basic))

    stats = EvTable(border="cells")
    for label, key in (("|cHP|n", "hp"), ("|cMP|n", "mp"), ("|cSP|n", "sp")):
        if data.get(key) is not None:
            stats.add_row(label, fmt(data.get(key)))
    for label, key in (
        ("|cDamage|n", "damage"),
        ("|cArmor|n", "armor"),
        ("|cInitiative|n", "initiative"),
    ):
        if data.get(key) is not None:
            stats.add_row(label, fmt(data.get(key)))
    if data.get("primary_stats"):
        stats.add_row("|cStats|n", fmt(data.get("primary_stats")))
    if data.get("modifiers"):
        stats.add_row("|cModifiers|n", fmt(data.get("modifiers")))
    if data.get("buffs"):
        stats.add_row("|cBuffs|n", fmt(data.get("buffs")))
    lines.append("\n|cCombat Stats|n")
    lines.append(str(stats))

    flags = EvTable(border="cells")
    add_row(flags, "|cAct Flags|n", "actflags")
    add_row(flags, "|cAffects|n", "affected_by")
    add_row(flags, "|cResists|n", "resistances")
    if data.get("attack_types"):
        flags.add_row("|cAttacks|n", fmt(data.get("attack_types")))
    if data.get("defense_types"):
        flags.add_row("|cDefenses|n", fmt(data.get("defense_types")))
    lines.append("\n|cCombat Flags|n")
    lines.append(str(flags))

    rewards = EvTable(border="cells")
    if data.get("exp_reward") is not None:
        rewards.add_row("|cXP Reward|n", fmt(data.get("exp_reward")))
    if "coin_drop" in data or "coins" in data:
        coins = data.get("coin_drop") or data.get("coins")
        if isinstance(coins, dict):
            from utils.currency import format_wallet

            coins = format_wallet(coins)
        if coins not in (None, "", [], {}):
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
    add_row(skills, "|cSkills|n", "skills")
    add_row(skills, "|cSpells|n", "spells")
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
    return _next_node(caller, "menunode_level")


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
    return _next_node(caller, "menunode_race")


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
    return _next_node(caller, "menunode_vnum")


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
        return _next_node(caller, "menunode_resources_prompt")
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
        return _next_node(caller, "menunode_loot_table")
    if string.lower().startswith("remove "):
        proto = string[7:].strip()
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
    skills = caller.ndb.buildnpc.get("skills", [])
    default = ", ".join(skills)
    npc_type = caller.ndb.buildnpc.get("npc_type", NPCType.BASE)
    suggested = ", ".join(get_skills_for_class(npc_type))
    text = "|wList any skills or attacks (comma separated)|n"
    if default:
        text += f" [default: {default}]"
    text += f"\nSuggested for {npc_type}: {suggested}"
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
    return _next_node(caller, "menunode_spells")


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
    return _next_node(caller, "menunode_ai")


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
        {"key": "3", "desc": "Edit Something", "goto": "menunode_review"},
        {"key": "4", "desc": "Cancel", "goto": _cancel},
    ]

    return text, options


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


def _create_npc(caller, raw_string, register=False, **kwargs):
    data = caller.ndb.buildnpc
    if not isinstance(data, dict):
        caller.msg("Error: NPC data missing. Aborting.")
        return None
    npc_type = data.get("npc_type", NPCType.BASE)
    if data.get("combat_class") and npc_type not in COMBATANT_TYPES:
        caller.msg("|rCombat class defined for non-combat NPC type.|n")
    tclass = NPC_TYPE_MAP[npc_type]
    tclass_path = f"{tclass.__module__}.{tclass.__name__}"
    role_mixins = [
        ROLE_MIXIN_MAP[r] for r in data.get("roles", []) if r in ROLE_MIXIN_MAP
    ]
    dyn_class = type("DynamicNPC", tuple([tclass, *role_mixins]), {})
    if data.get("edit_obj"):
        npc = data.get("edit_obj")
        if npc.__class__ != dyn_class:
            npc.swap_typeclass(dyn_class, clean_attributes=False)
    else:
        npc = create_object(dyn_class, key=data.get("key"), location=caller.location)

    old_vnum = getattr(caller.ndb, "mob_vnum", None)
    new_vnum = data.get("vnum")
    if old_vnum is not None and new_vnum is not None and int(old_vnum) != int(new_vnum):
        get_mobdb().delete_proto(int(old_vnum))
        if data.get("edit_obj"):
            npc.tags.remove(f"M{old_vnum}", category="vnum")
        caller.ndb.mob_vnum = new_vnum
    npc.db.desc = data.get("desc")
    npc.db.race = data.get("race")
    # accept legacy "sex" key
    gender = data.get("gender") or data.get("sex")
    metadata = {
        "type": data.get("npc_type", NPCType.BASE),
        "roles": [r for r in data.get("roles", []) if r],
        "combat_class": data.get("combat_class") or "",
        "gender": gender or "",
        "ai_type": data.get("ai_type") or "",
    }
    npc.db.metadata = metadata
    npc.db.weight = data.get("weight")
    if cc := metadata.get("combat_class"):
        npc.db.combat_class = cc
    if vnum := data.get("vnum"):
        npc.db.vnum = vnum
        npc.tags.add(f"M{vnum}", category="vnum")
    if guild := data.get("guild_affiliation"):
        npc.tags.add(guild, category="guild_affiliation")
    if markup := data.get("merchant_markup"):
        npc.db.merchant_markup = markup
    npc.db.behavior = data.get("behavior")
    npc.db.skills = data.get("skills")
    npc.db.spells = data.get("spells")
    npc.db.actflags = data.get("actflags")
    npc.db.affected_by = data.get("affected_by")
    npc.db.resistances = data.get("resistances")
    npc.db.bodyparts = data.get("bodyparts")
    npc.db.attack_types = data.get("attack_types")
    npc.db.defense_types = data.get("defense_types")
    npc.db.languages = data.get("languages")
    npc.db.modifiers = data.get("modifiers") or {}
    npc.db.buffs = data.get("buffs") or []
    mobprogs = data.get("mobprogs") or []
    npc.db.mobprogs = mobprogs
    npc.db.coin_drop = data.get("coin_drop") or {}
    npc.db.loot_table = data.get("loot_table") or []
    npc.db.exp_reward = data.get("exp_reward", 0)
    if script_path := data.get("script"):
        npc.db.metadata["script"] = script_path
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
            npc.db.natural_weapon["damage"] = data.get(
                "damage", npc.db.natural_weapon.get("damage", 1)
            )
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
        proto["metadata"] = metadata
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
        area = caller.location.db.area
        if data.get("vnum") is not None:
            try:
                mob_proto.register_prototype(proto, vnum=data["vnum"], area=area)
            except ValueError:
                if area:
                    from world.areas import get_area_vnum_range

                    rng = get_area_vnum_range(area)
                    if rng:
                        caller.msg(
                            f"VNUM {data['vnum']} outside {area} range {rng[0]}-{rng[1]}"
                        )
                        npc.db.vnum = None
                        finalize_mob_prototype(caller, npc)
                        return None
                caller.msg("Invalid VNUM for prototype.")
                npc.db.vnum = None
                finalize_mob_prototype(caller, npc)
                return None
        if area:
            from world import area_npcs

            area_npcs.add_area_npc(area, proto_key)
        caller.msg(f"NPC {npc.key} created and prototype saved.")
    else:
        caller.msg(f"NPC {npc.key} created.")
    finalize_mob_prototype(caller, npc)
    if register and npc.db.vnum is not None:
        caller.msg(
            f"✅ Mob saved and registered as VNUM {npc.db.vnum}. Spawn with: @mspawn M{npc.db.vnum}"
        )
    if register:
        caller.ndb.builder_saved = True
    caller.ndb.buildnpc = None
    return None


def _cancel(caller, raw_string, **kwargs):
    caller.msg("NPC creation cancelled.")
    script = caller.scripts.get("builder_autosave")
    if script:
        script[0].stop()
    caller.db.builder_autosave = None
    caller.ndb.buildnpc = None
    return None


def _on_menu_exit(caller, menu):
    """Warn user if menu exits with unsaved data."""
    # stop autosave script when menu closes
    script = caller.scripts.get("builder_autosave")
    if script:
        script[0].stop()
    if getattr(caller.ndb, "builder_saved", False):
        caller.ndb.builder_saved = False
        caller.db.builder_autosave = None
        return
    if getattr(caller.ndb, "buildnpc", None):
        caller.msg(
            "\u26a0\ufe0f You must choose ‘Yes & Save Prototype’ to make this NPC spawnable with @mspawn."
        )
        caller.ndb.buildnpc = None


def _gather_npc_data(npc):
    """Return a dict of editable NPC attributes."""
    meta = npc.db.metadata or {}
    return {
        "edit_obj": npc,
        "proto_key": npc.tags.get(category=PROTOTYPE_TAG_CATEGORY),
        "key": npc.key,
        "desc": npc.db.desc,
        "race": npc.db.race or "",
        "gender": meta.get("gender") or npc.db.gender or getattr(npc.db, "sex", ""),
        "weight": npc.db.weight or "",
        "roles": meta.get("roles")
        or npc.tags.get(category="npc_role", return_list=True)
        or [],
        "npc_type": next(
            (
                key
                for key, cls in NPC_TYPE_MAP.items()
                if f"{cls.__module__}.{cls.__name__}" == npc.typeclass_path
            ),
            NPCType.BASE,
        ),
        "combat_class": meta.get("combat_class") or npc.db.charclass or "",
        "creature_type": npc.db.creature_type or "humanoid",
        "equipment_slots": npc.db.equipment_slots or list(SLOT_ORDER),
        "level": npc.db.level or 1,
        "hp": npc.traits.health.base if npc.traits.get("health") else 0,
        "mp": npc.traits.mana.base if npc.traits.get("mana") else 0,
        "sp": npc.traits.stamina.base if npc.traits.get("stamina") else 0,
        "damage": (
            npc.db.natural_weapon.get("damage", 1) if npc.db.natural_weapon else 1
        ),
        "armor": npc.db.armor or 0,
        "initiative": getattr(npc.traits.get("initiative"), "base", 0),
        "primary_stats": npc.db.base_primary_stats or {},
        "behavior": npc.db.behavior or "",
        "skills": npc.db.skills or [],
        "spells": npc.db.spells or [],
        "ai_type": meta.get("ai_type") or npc.db.ai_type or "",
        "actflags": npc.db.actflags or [],
        "affected_by": npc.db.affected_by or [],
        "resistances": npc.db.resistances or [],
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
    if not npc.db.level or not (
        npc.db.combat_class or (npc.db.metadata or {}).get("combat_class")
    ):
        caller.msg("|rCannot finalize mob. Missing level or class.|n")
        return

    from world import stats as world_stats
    world_stats.apply_stats(npc)

    meta = npc.db.metadata or {}

    npc.tags.add("npc")
    npc_type = meta.get("type") or getattr(npc.db, "npc_type", None)
    if npc_type:
        npc.tags.add(npc_type, category="npc_type")
    roles = meta.get("roles") or getattr(npc.db, "roles", [])
    for role in make_iter(roles):
        if role:
            npc.tags.add(role, category="npc_role")

    if meta.get("gender"):
        npc.db.gender = meta["gender"]
    if meta.get("ai_type"):
        npc.db.ai_type = meta["ai_type"]
    if meta.get("combat_class"):
        npc.db.combat_class = meta["combat_class"]

    if npc.db.mobprogs and not npc.db.triggers:
        npc.db.triggers = mobprogs_to_triggers(npc.db.mobprogs)
    TriggerManager(npc).start_random_triggers()

    if meta.get("script"):
        try:
            script_cls = _import_script(meta["script"])
            if not npc.scripts.get(script_cls.__name__):
                npc.scripts.add(script_cls, key=script_cls.__name__)
        except Exception as err:  # pragma: no cover - log errors
            logger.log_err(f"Could not attach script {meta['script']}: {err}")

    if hasattr(npc, "at_npc_spawn"):
        try:
            npc.at_npc_spawn()
        except Exception as err:  # pragma: no cover - log errors
            logger.log_err(f"at_npc_spawn error on {npc}: {err}")

    npc.db.charclass = npc.db.combat_class
    stats = generate_base_stats(npc.db.combat_class, npc.db.level)
    for attr, trait in (("hp", "health"), ("mp", "mana"), ("sp", "stamina")):
        value = getattr(npc.traits.get(trait), "base", 0)
        if not value:
            value = stats[attr]
        setattr(npc.db, attr, value)
    if npc.db.armor is None:
        npc.db.armor = stats["armor"]
    if npc.db.initiative is None:
        npc.db.initiative = stats["initiative"]

    from world.mobregistry import register_mob_vnum

    if npc.db.vnum:
        register_mob_vnum(vnum=npc.db.vnum, prototype=npc)

    msg = f"|gMob '{npc.key}' finalized"
    if npc.db.vnum is not None:
        msg += f" with VNUM {npc.db.vnum}"
    msg += " and added to mob list.|n"
    caller.msg(msg)


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
        autosave = self.caller.db.builder_autosave
        if sub in ("restore", "discard") and autosave:
            if sub == "restore":
                self.caller.ndb.buildnpc = dict(autosave)
                self.caller.db.builder_autosave = None
                self.caller.scripts.add(BuilderAutosave, key="builder_autosave")
                state = OLCState(data=self.caller.ndb.buildnpc)
                startnode = (
                    "menunode_desc" if self.caller.ndb.buildnpc.get("key") else "menunode_key"
                )
                OLCEditor(
                    self.caller,
                    "commands.npc_builder",
                    startnode=startnode,
                    state=state,
                    validator=NPCValidator(),
                ).start()
            else:
                self.caller.db.builder_autosave = None
                self.msg("Autosave discarded.")
            return
        if autosave and sub not in ("restore", "discard"):
            self.msg("Autosave found. Use 'cnpc restore' to continue or 'cnpc discard' to start over.")
            return
        use_mob = self.cmdstring.lower() == "mobbuilder"
        if sub == "start":
            if not rest:
                self.msg("Usage: cnpc start <key>")
                return
            self.caller.ndb.buildnpc = {
                "key": rest.strip(),
                "race": "",
                "gender": "",
                "weight": "",
                "mobprogs": [],
                "npc_type": "base",
                "combat_class": "",
                "roles": [],
                "skills": [],
                "spells": [],
                "resistances": [],
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
            if use_mob:
                self.caller.ndb.buildnpc["use_mob"] = True
            self.caller.scripts.add(BuilderAutosave, key="builder_autosave")
            state = OLCState(data=self.caller.ndb.buildnpc)
            startnode = (
                "menunode_desc" if self.caller.ndb.buildnpc.get("key") else "menunode_key"
            )
            OLCEditor(
                self.caller,
                "commands.npc_builder",
                startnode=startnode,
                state=state,
                validator=NPCValidator(),
            ).start()
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
            if use_mob:
                self.caller.ndb.buildnpc["use_mob"] = True
            self.caller.scripts.add(BuilderAutosave, key="builder_autosave")
            state = OLCState(data=self.caller.ndb.buildnpc)
            startnode = (
                "menunode_desc" if self.caller.ndb.buildnpc.get("key") else "menunode_key"
            )
            OLCEditor(
                self.caller,
                "commands.npc_builder",
                startnode=startnode,
                state=state,
                validator=NPCValidator(),
            ).start()
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
                    if (
                        proto_dict.get("combat_class")
                        and NPCType.from_str(proto_dict.get("npc_type", "base"))
                        not in COMBATANT_TYPES
                    ):
                        self.msg("|rCombat class defined for non-combat NPC type.|n")
                    obj = spawner.spawn(proto_dict)[0]
                else:
                    # proto is a path string
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
        data = self.caller.ndb.buildnpc
        mob_db = get_mobdb()
        vnum = data.get("vnum") or npc.db.vnum
        finalized = vnum is not None and int(vnum) in mob_db.db.vnums
        status = "✅" if finalized else "🚫"
        roles = data.get("roles") or []
        if isinstance(roles, str):
            roles = [roles]
        primary = roles[0] if roles else "-"
        level = data.get("level") or npc.db.level or "-"
        self.msg(f"{status} {primary} L{level}")
        state = OLCState(data=self.caller.ndb.buildnpc)
        OLCEditor(
            self.caller,
            "commands.npc_builder",
            startnode="menunode_review",
            state=state,
            validator=NPCValidator(),
        ).start()


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
            vnum = int(arg)
            proto = get_prototype(vnum)
            if not proto:
                if vnum_registry.validate_vnum(vnum, "npc"):
                    self.msg(
                        "❌ Invalid VNUM. The prototype was never finalized or saved."
                    )
                else:
                    self.msg("Unknown NPC prototype.")
                return
            if (
                proto.get("combat_class")
                and NPCType.from_str(proto.get("npc_type", "base"))
                not in COMBATANT_TYPES
            ):
                self.msg("|rCombat class defined for non-combat NPC type.|n")
            try:
                obj = spawn_from_vnum(vnum, location=self.caller.location)
            except ValueError as err:
                self.msg(str(err))
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
            if (
                proto.get("combat_class")
                and NPCType.from_str(proto.get("npc_type", "base"))
                not in COMBATANT_TYPES
            ):
                self.msg("|rCombat class defined for non-combat NPC type.|n")
            tclass = NPC_TYPE_MAP[NPCType.from_str(proto.get("npc_type", "base"))]
            proto = dict(proto)
            proto.setdefault("typeclass", f"{tclass.__module__}.{tclass.__name__}")

            base_cls = proto["typeclass"]
            if isinstance(base_cls, str):
                module, clsname = base_cls.rsplit(".", 1)
                base_cls_obj = getattr(__import__(module, fromlist=[clsname]), clsname)
            else:
                base_cls_obj = base_cls

            from typeclasses.characters import NPC
            from typeclasses.npcs import BaseNPC

            if not issubclass(base_cls_obj, NPC):
                logger.log_warn(
                    f"Prototype {key}: {base_cls_obj} is not a subclass of NPC; using BaseNPC."
                )
                base_cls_obj = BaseNPC

            proto["typeclass"] = base_cls_obj
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
