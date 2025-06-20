from __future__ import annotations

from typing import Iterable

from .ai_controller import Behavior, run_behaviors
from ..combat_actions import AttackAction
from ..engine import CombatEngine
from ..combat_skills import SKILL_CLASSES
from ..scripts import queue_skill, queue_spell, get_spell


def _default_behaviors(npc) -> Iterable[Behavior]:
    """Yield behaviors for any skills or spells the NPC knows."""

    # Spells are highest priority if the NPC has mana for them.
    def make_spell_behavior(spell_key, spell):
        def check(engine, n, t):
            mana = getattr(n.traits, "mana", None)
            return mana and mana.current >= spell.mana_cost and n.cooldowns.ready(spell.key)

        def act(engine, n, t):
            queue_spell(n, spell_key, t, engine=engine)

        return Behavior(30, check, act)

    for sp in getattr(npc.db, "spells", []):
        spell_key = sp.key if hasattr(sp, "key") else sp
        spell = get_spell(spell_key)
        if not spell:
            continue
        yield make_spell_behavior(spell_key, spell)

    # Skills next.
    def instantiate_skill(cls):
        try:
            return cls()
        except TypeError:
            obj = cls.__new__(cls)
            for attr in dir(cls):
                if attr.startswith("__"):
                    continue
                try:
                    setattr(obj, attr, getattr(cls, attr))
                except AttributeError:
                    pass
            return obj

    def make_skill_behavior(skill_cls):
        skill = instantiate_skill(skill_cls)

        def check(engine, n, t):
            stam = getattr(n.traits, "stamina", None)
            return stam and stam.current >= getattr(skill, "stamina_cost", 0) and n.cooldowns.ready(getattr(skill, "name", ""))

        def act(engine, n, t):
            queue_skill(n, skill, t, engine=engine)

        return Behavior(20, check, act)

    for sk in getattr(npc.db, "skills", []):
        skill_cls = SKILL_CLASSES.get(sk)
        if not skill_cls:
            continue
        yield make_skill_behavior(skill_cls)

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

    if not target:
        return

    # check for low health hook
    if hasattr(npc, "on_low_hp"):
        cur = getattr(getattr(npc.traits, "health", None), "value", getattr(npc, "hp", 0))
        max_hp = getattr(getattr(npc.traits, "health", None), "max", getattr(npc, "max_hp", cur))
        if max_hp and cur / max_hp <= 0.3:
            npc.on_low_hp(engine)

    behaviors = list(_default_behaviors(npc))
    run_behaviors(engine, npc, target, behaviors)
