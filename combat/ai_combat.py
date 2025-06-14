"""Combat AI utilities using a simple priority system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

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


def _default_behaviors(npc) -> Iterable[Behavior]:
    """Yield behaviors for any skills or spells the NPC knows."""

    # Spells are highest priority if the NPC has mana for them.
    def make_spell_behavior(spell_key, spell):
        def check(engine, n, t):
            mana = getattr(n.traits, "mana", None)
            return mana and mana.current >= spell.mana_cost and n.cooldowns.ready(spell.key)

        def act(engine, n, t):
            if engine:
                engine.queue_action(n, SpellAction(n, spell_key, t))
            else:
                n.cast_spell(spell_key, target=t)

        return Behavior(30, check, act)

    for sp in getattr(npc.db, "spells", []):
        spell_key = sp.key if hasattr(sp, "key") else sp
        spell = SPELLS.get(spell_key)
        if not spell:
            continue
        yield make_spell_behavior(spell_key, spell)

    # Skills next.
    def make_skill_behavior(skill):
        def check(engine, n, t):
            stam = getattr(n.traits, "stamina", None)
            return stam and stam.current >= skill.stamina_cost and n.cooldowns.ready(skill.name)

        def act(engine, n, t):
            if engine:
                engine.queue_action(n, SkillAction(n, skill, t))
            else:
                n.use_skill(skill.name, target=t)

        return Behavior(20, check, act)

    for sk in getattr(npc.db, "skills", []):
        skill_cls = SKILL_CLASSES.get(sk)
        if not skill_cls:
            continue
        skill = skill_cls()
        yield make_skill_behavior(skill)

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

