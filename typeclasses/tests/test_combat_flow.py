import unittest
from unittest.mock import MagicMock, patch

from combat.combat_engine import CombatEngine
from combat.combat_actions import AttackAction, SkillAction, SpellAction, CombatResult, Action
from combat.combat_skills import ShieldBash
from combat.damage_types import DamageType
from combat.ai_combat import npc_take_turn


class Dummy:
    def __init__(self, hp=10):
        self.hp = hp
        self.key = "dummy"
        self.location = MagicMock()
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=0)
        self.traits.health = MagicMock(value=hp, max=hp)
        self.traits.mana = MagicMock(current=20)
        self.traits.stamina = MagicMock(current=20)
        self.cooldowns = MagicMock()
        self.cooldowns.ready.return_value = True
        self.tags = MagicMock()
        self.wielding = []
        self.db = type(
            "DB",
            (),
            {
                "temp_bonuses": {},
                "status_effects": {},
                "active_effects": {},
                "get": lambda *a, **k: 0,
            },
        )()
        self.attack = MagicMock()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.cast_spell = MagicMock()
        self.use_skill = MagicMock()


class KillAction(Action):
    def resolve(self):
        self.target.hp = 0
        return CombatResult(self.actor, self.target, "boom")


class TestAttackAction(unittest.TestCase):
    def test_attack_deals_damage(self):
        attacker = Dummy()
        defender = Dummy()
        weapon = MagicMock()
        weapon.damage = 5
        weapon.damage_type = DamageType.SLASHING
        weapon.at_attack = MagicMock()
        attacker.wielding = [weapon]
        attacker.location = defender.location

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))
        with patch("combat.combat_actions.utils.inherits_from", return_value=True), \
             patch("world.system.state_manager.apply_regen"), \
             patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        self.assertEqual(defender.hp, 5)
        weapon.at_attack.assert_not_called()

    def test_attack_damage_scaled_by_stats(self):
        attacker = Dummy()
        defender = Dummy()
        weapon = MagicMock()
        weapon.damage = 5
        weapon.damage_type = DamageType.SLASHING
        weapon.at_attack = MagicMock()
        attacker.wielding = [weapon]
        attacker.location = defender.location

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))
        with patch("combat.combat_actions.utils.inherits_from", return_value=True), \
             patch("world.system.state_manager.apply_regen"), \
             patch("random.randint", return_value=0), \
             patch("world.system.state_manager.get_effective_stat") as mock_get:
            def getter(obj, stat):
                if obj is attacker and stat == "STR":
                    return 10
                if obj is attacker and stat == "DEX":
                    return 5
                return 0

            mock_get.side_effect = getter
            engine.start_round()
            engine.process_round()

        self.assertEqual(defender.hp, 4)


class TestCombatVictory(unittest.TestCase):
    def test_handle_defeat_removes_participant(self):
        a = Dummy()
        b = Dummy()
        a.location = b.location
        engine = CombatEngine([a, b], round_time=0)
        engine.queue_action(a, KillAction(a, b))
        with patch("world.system.state_manager.apply_regen"):
            engine.start_round()
            engine.process_round()
        self.assertNotIn(b, [p.actor for p in engine.participants])


class TestNPCBehaviors(unittest.TestCase):
    def test_low_hp_triggers_callback(self):
        npc = Dummy()
        npc.traits.health.value = 2
        npc.traits.health.max = 10
        npc.on_low_hp = MagicMock()
        target = Dummy()
        npc_take_turn(None, npc, target)
        npc.on_low_hp.assert_called()




class TestSpellExample(unittest.TestCase):
    def test_spell_action_calls_cast(self):
        caster = Dummy()
        target = Dummy()
        caster.location = target.location
        caster.cast_spell = MagicMock()
        engine = CombatEngine([caster, target], round_time=0)
        engine.queue_action(caster, SpellAction(caster, "fireball", target))
        with patch("world.system.state_manager.apply_regen"), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()
        caster.cast_spell.assert_called_with("fireball", target)

