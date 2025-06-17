from evennia.utils import make_iter, dedent, delay
from olc.base import OLCEditor, OLCState, OLCValidator
from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.prototypes import spawner
from utils.mob_proto import spawn_from_vnum, get_prototype, apply_proto_items
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
from copy import deepcopy
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
    ("Long Description", "menunode_longdesc"),
    ("Level", "menunode_level"),
    ("Race", "menunode_race"),
    ("NPC Type", "menunode_npc_type"),
    ("Gender", "menunode_gender"),
    ("Weight", "menunode_weight"),
    ("VNUM", "menunode_vnum"),
    ("Creature Type", "menunode_creature_type"),
    ("Combat Class", "menunode_combat_class"),
    ("Role Details", "menunode_role_details"),
    ("Rewards", "menunode_exp_reward"),
    ("EXP Reward", "menunode_exp_reward"),
    ("Edit XP reward", "menunode_exp_reward"),
    ("Coin Drop", "menunode_coin_drop"),
    ("Loot Table", "menunode_loot_table"),
    ("Combat Stats", "menunode_resources_prompt"),
    ("Resources", "menunode_resources_prompt"),
    ("Combat Values", "menunode_combat_values"),
    ("Modifiers", "menunode_modifiers"),
    ("Primary Stats", "menunode_secondary_stats_prompt"),
    ("Behavior", "menunode_behavior"),
    ("Skills", "menunode_skills"),
    ("Spells", "menunode_spells"),
    ("AI Type", "menunode_ai"),
    ("Combat Flags", "menunode_actflags"),
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
            return ", ".join(f"{k}({v}%)" for k, v in value.items())
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
    add_row(basic, "|cLong Desc|n", "long_desc")
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
            if "amount" in e:
                part += f" x{e['amount']}"
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
    npc.db.long_desc = data.get("long_desc")
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
        script[0].delete()
    caller.db.builder_autosave = None
    caller.ndb.buildnpc = None
    return None


def _on_menu_exit(caller, menu):
    """Warn user if menu exits with unsaved data."""
    # stop autosave script when menu closes
    script = caller.scripts.get("builder_autosave")
    if script:
        script[0].stop()
        script[0].delete()
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
        "long_desc": npc.db.long_desc,
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
        "skills": npc.db.skills or {},
        "spells": npc.db.spells or {},
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
        "spawn": npc.db.spawn or {},
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
        npc.tags.add("npc_ai")
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

    if not npc.db.exp_reward:
        npc.db.exp_reward = (npc.db.level or 1) * settings.DEFAULT_XP_PER_LEVEL

    from world.mobregistry import register_mob_vnum

    if npc.db.vnum:
        register_mob_vnum(vnum=npc.db.vnum, prototype=npc)

    msg = f"|gMob '{npc.key}' finalized"
    if npc.db.vnum is not None:
        msg += f" with VNUM {npc.db.vnum}"
    msg += " and added to mob list.|n"

    from world.system import stat_manager
    stat_manager.refresh_stats(npc)

    caller.msg(msg)


def _ensure_autosave_script(caller) -> None:
    """(Re)start the autosave script, removing any existing copy."""
    script = caller.scripts.get("builder_autosave")
    if script:
        script[0].stop()
        script[0].delete()
    caller.scripts.add(BuilderAutosave, key="builder_autosave")


class CmdCNPC(Command):
    """Create or edit an NPC using a guided menu."""

    key = "cnpc"
    aliases = ["createnpc", "mobbuilder"]
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg(
                "Usage: cnpc start <key> | cnpc edit <npc> | cnpc clone <proto> [= new_key] | cnpc dev_spawn <proto>"
            )
            return
        parts = self.args.split(None, 1)
        sub = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        autosave = self.caller.db.builder_autosave
        if sub in ("restore", "discard") and autosave:
            if sub == "restore":
                self.caller.ndb.buildnpc = dict(autosave)
                self.caller.ndb.buildnpc_orig = dict(self.caller.ndb.buildnpc)
                self.caller.db.builder_autosave = None
                _ensure_autosave_script(self.caller)
                state = OLCState(data=self.caller.ndb.buildnpc, original=dict(self.caller.ndb.buildnpc))
                startnode = (
                    "menunode_desc" if self.caller.ndb.buildnpc.get("key") else "menunode_key"
                )
                OLCEditor(
                    self.caller,
                    "world.menus.mob_builder_menu",
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
                "spawn": {},
                "merchant_markup": 1.0,
                "script": "",
                "modifiers": {},
                "buffs": [],
            }
            if use_mob:
                self.caller.ndb.buildnpc["use_mob"] = True
            self.caller.ndb.buildnpc_orig = dict(self.caller.ndb.buildnpc)
            _ensure_autosave_script(self.caller)
            state = OLCState(data=self.caller.ndb.buildnpc, original=dict(self.caller.ndb.buildnpc))
            startnode = (
                "menunode_desc" if self.caller.ndb.buildnpc.get("key") else "menunode_key"
            )
            OLCEditor(
                self.caller,
                "world.menus.mob_builder_menu",
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
            self.caller.ndb.buildnpc_orig = dict(self.caller.ndb.buildnpc)
            if use_mob:
                self.caller.ndb.buildnpc["use_mob"] = True
            _ensure_autosave_script(self.caller)
            state = OLCState(data=self.caller.ndb.buildnpc, original=dict(self.caller.ndb.buildnpc))
            startnode = (
                "menunode_desc" if self.caller.ndb.buildnpc.get("key") else "menunode_key"
            )
            OLCEditor(
                self.caller,
                "world.menus.mob_builder_menu",
                startnode=startnode,
                state=state,
                validator=NPCValidator(),
            ).start()
            return
        if sub == "clone":
            if not rest:
                self.msg("Usage: cnpc clone <prototype> [= <new_key>]")
                return
            proto_key, _, new_key = rest.partition("=")
            proto_key = proto_key.strip()
            new_key = new_key.strip() if new_key else ""
            from world import prototypes

            proto = prototypes.get_npc_prototypes().get(proto_key)
            if not proto:
                self.msg("Unknown NPC prototype.")
                return
            data = dict(proto)
            if new_key:
                data["key"] = new_key
            self.caller.ndb.buildnpc = data
            self.caller.ndb.buildnpc_orig = dict(self.caller.ndb.buildnpc)
            if use_mob:
                self.caller.ndb.buildnpc["use_mob"] = True
            _ensure_autosave_script(self.caller)
            state = OLCState(data=self.caller.ndb.buildnpc, original=dict(self.caller.ndb.buildnpc))
            OLCEditor(
                self.caller,
                "world.menus.mob_builder_menu",
                startnode="menunode_review",
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
        self.msg(
            "Usage: cnpc start <key> | cnpc edit <npc> | cnpc clone <proto> [= new_key] | cnpc dev_spawn <proto>"
        )


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
        finalized = vnum is not None and str(vnum) in mob_db.db.vnums
        status = "✅" if finalized else "🚫"
        roles = data.get("roles") or []
        if isinstance(roles, str):
            roles = [roles]
        primary = roles[0] if roles else "-"
        level = data.get("level") or npc.db.level or "-"
        self.msg(f"{status} {primary} L{level}")
        state = OLCState(data=self.caller.ndb.buildnpc, original=dict(self.caller.ndb.buildnpc))
        OLCEditor(
            self.caller,
            "world.menus.mob_builder_menu",
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
            apply_proto_items(obj, proto)
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


class CmdMSpawn(Command):
    """Spawn a mob prototype."""

    key = "@mspawn"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        arg = self.args.strip()
        if not arg:
            self.msg("Usage: @mspawn <prototype>")
            return

        vnum = None
        if arg.isdigit():
            vnum = int(arg)
        elif arg.upper().startswith("M") and arg[1:].isdigit():
            vnum = int(arg[1:])

        if vnum is not None:
            proto = get_prototype(vnum)
            if not proto:
                if vnum_registry.validate_vnum(vnum, "npc"):
                    self.msg(
                        f"Prototype {vnum} not finalized. Use editnpc {vnum} and finalize with 'Yes & Save'."
                    )
                else:
                    self.msg("Invalid VNUM.")
                return
            try:
                obj = spawn_from_vnum(vnum, location=self.caller.location)
            except ValueError as err:
                self.msg(str(err))
                return
            proto_key = vnum
        else:
            mob_db = get_mobdb()
            vmatch = next((num for num, p in mob_db.db.vnums.items() if p.get("key") == arg), None)
            if vmatch is not None:
                try:
                    obj = spawn_from_vnum(vmatch, location=self.caller.location)
                except ValueError as err:
                    self.msg(str(err))
                    return
                proto_key = vmatch
            else:
                from world import prototypes

                registry = prototypes.get_npc_prototypes()
                proto_key = arg if arg in registry else f"mob_{arg}"
                proto = registry.get(proto_key)
                if not proto:
                    self.msg("Prototype not found.")
                    return
                tclass = NPC_TYPE_MAP.get(
                    NPCType.from_str(proto.get("npc_type", "base")),
                    BaseNPC,
                )
                proto = dict(proto)
                proto.setdefault("typeclass", f"{tclass.__module__}.{tclass.__name__}")
                obj = spawner.spawn(proto)[0]
                obj.move_to(self.caller.location, quiet=True)
                if proto.get("vnum"):
                    obj.db.vnum = proto["vnum"]
                    obj.tags.add(f"M{proto['vnum']}", category="vnum")
                apply_proto_items(obj, proto)
        obj.db.spawn_room = self.caller.location
        obj.db.prototype_key = proto_key

        from evennia.scripts.models import ScriptDB
        script = ScriptDB.objects.filter(db_key="spawn_manager").first()
        if script and hasattr(script, "record_spawn"):
            script.record_spawn(proto_key, self.caller.location)

        self.msg(f"Spawned {obj.key}.")


class CmdMobPreview(Command):
    """Spawn a mob prototype briefly for preview."""

    key = "@mobpreview"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        key = self.args.strip()
        if not key:
            self.msg("Usage: @mobpreview <prototype>")
            return
        if key.isdigit():
            try:
                obj = spawn_from_vnum(int(key), location=self.caller.location)
            except ValueError as err:
                self.msg(str(err))
                return
        else:
            from world import prototypes

            registry = prototypes.get_npc_prototypes()
            proto = registry.get(key) or registry.get(f"mob_{key}")
            if not proto:
                self.msg("Prototype not found.")
                return
            tclass = NPC_TYPE_MAP.get(
                NPCType.from_str(proto.get("npc_type", "base")),
                BaseNPC,
            )
            proto = dict(proto)
            proto.setdefault("typeclass", f"{tclass.__module__}.{tclass.__name__}")
            obj = spawner.spawn(proto)[0]
            obj.move_to(self.caller.location, quiet=True)
            apply_proto_items(obj, proto)
        delay(30, obj.delete)
        self.msg(f"Previewing {obj.key}. It will vanish soon.")


from .mob_builder_commands import CmdMStat as CmdMStat, CmdMList as CmdMList


class CmdMobTemplate(Command):
    """Load a predefined mob template into the current build."""

    key = "@mobtemplate"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        from world.templates.mob_templates import MOB_TEMPLATES, get_template

        arg = self.args.strip().lower()
        if not arg or arg == "list":
            names = ", ".join(sorted(MOB_TEMPLATES))
            self.msg(f"Available templates: {names}")
            return
        data = get_template(arg)
        if not data:
            self.msg("Unknown template.")
            return
        self.caller.ndb.buildnpc = self.caller.ndb.buildnpc or {}
        for key, val in data.items():
            self.caller.ndb.buildnpc[key] = deepcopy(val)
        if not hasattr(self.caller.ndb, "buildnpc_orig"):
            self.caller.ndb.buildnpc_orig = dict(self.caller.ndb.buildnpc)
        self.msg(f"Template '{arg}' loaded into builder.")


class CmdQuickMob(Command):
    """Spawn and register a mob from a template in one step."""

    key = "@quickmob"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        from world.templates.mob_templates import get_template

        args = self.args.strip()
        if not args:
            self.msg("Usage: @quickmob <key> [template]")
            return

        parts = args.split(None, 1)
        key = parts[0]
        template = parts[1] if len(parts) > 1 else "warrior"

        data = get_template(template)
        if not data:
            self.msg("Unknown template.")
            return

        area = self.caller.location.db.area if self.caller.location else None
        if area:
            try:
                vnum = vnum_registry.get_next_vnum_for_area(
                    area,
                    "npc",
                    builder=self.caller.key,
                )
            except Exception:
                vnum = vnum_registry.get_next_vnum("npc")
        else:
            vnum = vnum_registry.get_next_vnum("npc")

        data = dict(data)
        data.update({"key": key, "vnum": vnum, "use_mob": True})
        self.caller.ndb.buildnpc = data
        self.caller.ndb.buildnpc_orig = dict(self.caller.ndb.buildnpc)
        _ensure_autosave_script(self.caller)
        state = OLCState(data=self.caller.ndb.buildnpc, original=dict(self.caller.ndb.buildnpc))
        OLCEditor(
            self.caller,
            "commands.npc_builder",
            startnode="menunode_review",
            state=state,
            validator=NPCValidator(),
        ).start()
