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

    def get_attack_weapon(self):
        if self.wielding:
            return self.wielding[0]
        if getattr(self.db, "natural_weapon", None):
            return self.db.natural_weapon
        from typeclasses.gear import BareHand
        return BareHand()


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

        with patch("world.system.state_manager.apply_regen"), \
             patch("world.system.state_manager.get_effective_stat", return_value=0), \
             patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.engine.combat_math.roll_evade", return_value=False), \
             patch("combat.engine.combat_math.roll_parry", return_value=False), \
             patch("combat.engine.combat_math.roll_block", return_value=False), \
             patch("evennia.utils.delay"):
            engine.start_round()
            engine.process_round()

        # Base damage of 4 should be increased by 25% from Unarmed proficiency
        # resulting in 5 damage dealt
        self.assertEqual(defender.hp, 5)

    def test_barehand_damage_unskilled(self):
        attacker = Dummy()
        defender = Dummy()
        attacker.location = defender.location
        attacker.db.skills = []
        attacker.db.proficiencies = {}

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))

        with patch("world.system.state_manager.apply_regen"), \
             patch("combat.engine.combat_math.CombatMath.check_hit", return_value=(True, "")) as mock_hit, \
             patch("combat.engine.combat_math.CombatMath.apply_critical", side_effect=lambda a, t, d: (d, False)), \
             patch("combat.engine.combat_math.roll_evade", return_value=False), \
             patch("combat.engine.combat_math.roll_parry", return_value=False), \
             patch("combat.engine.combat_math.roll_block", return_value=False), \
             patch("combat.engine.combat_math.roll_dice_string", return_value=4), \
             patch("world.system.state_manager.get_effective_stat", return_value=0), \
             patch("evennia.utils.delay"), \
             patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        self.assertEqual(defender.hp, 6)
        from unittest.mock import call
        self.assertIn(call(attacker, defender, bonus=-35), mock_hit.call_args_list)

    def test_barehand_damage_hand_to_hand(self):
        attacker = Dummy()
        defender = Dummy()
        attacker.location = defender.location
        attacker.db.skills = ["Hand-to-Hand"]
        attacker.db.proficiencies = {"Hand-to-Hand": 30}

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))

        with patch("world.system.state_manager.apply_regen"), \
             patch("combat.engine.combat_math.CombatMath.check_hit", return_value=(True, "")) as mock_hit, \
             patch("combat.engine.combat_math.CombatMath.apply_critical", side_effect=lambda a, t, d: (d, False)), \
             patch("combat.engine.combat_math.roll_evade", return_value=False), \
             patch("combat.engine.combat_math.roll_parry", return_value=False), \
             patch("combat.engine.combat_math.roll_block", return_value=False), \
             patch("combat.engine.combat_math.roll_dice_string", return_value=3), \
             patch("world.system.state_manager.get_effective_stat", return_value=20), \
             patch("evennia.utils.delay"), \
             patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        self.assertEqual(defender.hp, 0)
        from unittest.mock import call
        self.assertIn(call(attacker, defender, bonus=2), mock_hit.call_args_list)
