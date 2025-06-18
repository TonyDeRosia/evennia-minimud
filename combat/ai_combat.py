"""Combat AI utilities using a simple priority system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator, Tuple, Any
from random import random
import re

from .combat_utils import check_distance
from world.system import state_manager

from .combat_actions import AttackAction, SkillAction, SpellAction
from .engine import CombatEngine
from .combat_skills import SKILL_CLASSES
from world.spells import SPELLS


@dataclass(order=True)
class Behavior:
    """A prioritized behavior condition/action pair."""

    priority: int
    check: Callable[[CombatEngine | None, object, object], bool] = field(compare=False)
    act: Callable[[CombatEngine | None, object, object], None] = field(compare=False)


def _iter_abilities(data: Any) -> Iterator[Tuple[str, int]]:
    """Yield ``(name, chance)`` pairs from ``data``.

    Args:
        data: Iterable or mapping of ability entries. List items may include
            a chance value using ``"name(25%)"`` notation. Dictionary values
            are interpreted as chance percentages.

    Yields:
        Tuple[str, int]: Ability key/name and usage chance.
    """

    if not data:
        return

    if isinstance(data, dict):
        items = data.items()
    else:
        items = [(entry, None) for entry in data]

    for name, chance in items:
        abil_name = name
        perc = chance

        if isinstance(abil_name, str):
            match = re.match(r"\s*(.+?)\s*\((\d+)%\)\s*$", abil_name)
            if match:
                abil_name = match.group(1)
                perc = match.group(2)

        if hasattr(abil_name, "key"):
            abil_name = abil_name.key
        elif hasattr(abil_name, "name"):
            abil_name = abil_name.name

        if isinstance(perc, str):
            m = re.match(r"(\d+)", perc)
            perc = int(m.group(1)) if m else 100
        elif isinstance(perc, (int, float)):
            perc = int(perc)
        else:
            perc = 100

        yield str(abil_name), perc


def _default_behaviors(npc) -> Iterable[Behavior]:
    """Yield behaviors for any skills or spells the NPC knows."""

    # Spells are highest priority if the NPC has mana for them.
    def make_spell_behavior(spell_key: str, spell, chance: int):
        def check(engine, n, t):
            if random() > chance / 100:
                return False
            if state_manager.has_status(n, "stunned") or state_manager.has_status(n, "silenced"):
                return False
            mana = getattr(n.traits, "mana", None)
            if not (mana and mana.current >= spell.mana_cost and n.cooldowns.ready(spell.key)):
                return False
            action = SpellAction(n, spell_key, t)
            if not check_distance(n, t, action.range):
                return False
            return True

        def act(engine, n, t):
            if engine:
                engine.queue_action(n, SpellAction(n, spell_key, t))
            else:
                n.cast_spell(spell_key, target=t)

        return Behavior(30, check, act)

    for name, chance in _iter_abilities(getattr(npc.db, "spells", [])):
        spell_key = name
        spell = SPELLS.get(spell_key)
        if not spell:
            continue
        yield make_spell_behavior(spell_key, spell, chance)

    # Skills next.
    def make_skill_behavior(skill, chance: int):
        def check(engine, n, t):
            if random() > chance / 100:
                return False
            if state_manager.has_status(n, "stunned") or state_manager.has_status(n, "silenced"):
                return False
            stam = getattr(n.traits, "stamina", None)
            if not (stam and stam.current >= skill.stamina_cost and n.cooldowns.ready(skill.name)):
                return False
            action = SkillAction(n, skill, t)
            if not check_distance(n, t, action.range):
                return False
            return True

        def act(engine, n, t):
            if engine:
                engine.queue_action(n, SkillAction(n, skill, t))
            else:
                n.use_skill(skill.name, target=t)

        return Behavior(20, check, act)

    for name, chance in _iter_abilities(getattr(npc.db, "skills", [])):
        skill_cls = SKILL_CLASSES.get(name)
        if not skill_cls:
            continue
        skill = skill_cls()
        yield make_skill_behavior(skill, chance)

    # Fallback to a normal attack.
    def atk_check(engine, n, t):
        return bool(t and getattr(t, "hp", 0) > 0)

    def atk_act(engine, n, t):
        if engine:
            engine.queue_action(n, AttackAction(n, t))
        else:
            weapon = n.wielding[0] if getattr(n, "wielding", None) else n
            n.attack(t, weapon)

    yield Behavior(0, atk_check, atk_act)


def npc_take_turn(engine: CombatEngine | None, npc, target) -> None:
    """Select and queue a combat action for ``npc``."""

    if hasattr(npc, "on_environment"):
        npc.on_environment(engine)

    if not target or getattr(target, "hp", 0) <= 0:
        return

    # check for low health hook
    if hasattr(npc, "on_low_hp"):
        cur = getattr(getattr(npc.traits, "health", None), "value", getattr(npc, "hp", 0))
        max_hp = getattr(getattr(npc.traits, "health", None), "max", getattr(npc, "max_hp", cur))
        if max_hp and cur / max_hp <= 0.3:
            npc.on_low_hp(engine)

    behaviors = sorted(list(_default_behaviors(npc)), reverse=True)
    for beh in behaviors:
        if beh.check(engine, npc, target):
            beh.act(engine, npc, target)
            break

