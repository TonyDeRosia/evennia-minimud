import unittest
from unittest.mock import MagicMock, patch

from combat.engine import CombatEngine
from combat.combat_actions import AttackAction
from combat.damage_types import DamageType


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
                "skills": ["Unarmed"],
                "proficiencies": {"Unarmed": 50},
                "skill_uses": {},
            },
        )()
        self.attack = MagicMock()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.cast_spell = MagicMock()
        self.use_skill = MagicMock()


class TestUnarmedAutoAttack(unittest.TestCase):
    def test_unarmed_auto_attack_bonus_damage(self):
        attacker = Dummy()
        defender = Dummy()
        attacker.location = defender.location
        attacker.db.combat_target = defender
        attacker.db.natural_weapon = {
            "damage": 4,
            "damage_type": DamageType.BLUDGEONING,
        }

        engine = CombatEngine([attacker, defender], round_time=0)

        with patch("combat.combat_actions.utils.inherits_from", return_value=True), \
             patch("world.system.state_manager.apply_regen"), \
             patch("world.system.state_manager.get_effective_stat", return_value=0), \
             patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.actions.utils.roll_evade", return_value=False), \
             patch("combat.actions.utils.roll_parry", return_value=False), \
             patch("combat.actions.utils.roll_block", return_value=False), \
             patch("evennia.utils.delay"):
            engine.start_round()
            engine.process_round()

        # Base damage of 4 should be increased by 25% from Unarmed proficiency
        # resulting in 5 damage dealt
        self.assertEqual(defender.hp, 5)
