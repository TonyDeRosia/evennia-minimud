"""Combat AI utilities using a simple priority system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from .combat_actions import AttackAction, SkillAction, SpellAction
from .combat_engine import CombatEngine
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
    for sp in getattr(npc.db, "spells", []):
        spell_key = sp.key if hasattr(sp, "key") else sp
        spell = SPELLS.get(spell_key)
        if not spell:
            continue

        def check(engine, n, t, sk=spell):
            mana = getattr(n.traits, "mana", None)
            return mana and mana.current >= sk.mana_cost and n.cooldowns.ready(sk.key)

        def act(engine, n, t, sk=spell_key):
            if engine:
                engine.queue_action(n, SpellAction(n, sk, t))
            else:
                n.cast_spell(sk, target=t)

        yield Behavior(30, check, act)

    # Skills next.
    for sk in getattr(npc.db, "skills", []):
        skill_cls = SKILL_CLASSES.get(sk)
        if not skill_cls:
            continue
        skill = skill_cls()

        def check(engine, n, t, s=skill):
            stam = getattr(n.traits, "stamina", None)
            return stam and stam.current >= s.stamina_cost and n.cooldowns.ready(s.name)

        def act(engine, n, t, s=skill):
            if engine:
                engine.queue_action(n, SkillAction(n, s, t))
            else:
                n.use_skill(s.name, target=t)

        yield Behavior(20, check, act)

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

