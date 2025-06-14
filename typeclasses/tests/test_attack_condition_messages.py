from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from combat.combat_utils import get_condition_msg
from typeclasses.gear import BareHand


class TestAttackConditionMessages(EvenniaTest):
    """Ensure condition messages broadcast after attacks."""

    def setUp(self):
        super().setUp()
        # ensure room messages can be inspected
        self.room1.msg_contents = MagicMock()
        self.char1.location = self.room1
        self.char2.location = self.room1

    def _simple_damage(self, attacker, target, amount, **kwargs):
        target.traits.health.current -= amount
        return amount

    def _expect_no_condition_message(self, target):
        expected = get_condition_msg(
            target.traits.health.current, target.traits.health.max
        )
        calls = [c.args[0] for c in self.room1.msg_contents.call_args_list]
        self.assertFalse(any(f"The {target.key} {expected}" in msg for msg in calls))

    def test_barehand_condition(self):
        self.char2.at_damage = self._simple_damage
        with patch("world.system.stat_manager.check_hit", return_value=True), patch(
            "combat.combat_utils.roll_evade",
            return_value=False,
        ), patch("combat.combat_utils.roll_parry", return_value=False), patch(
            "combat.combat_utils.roll_block",
            return_value=False,
        ), patch("world.system.stat_manager.roll_crit", return_value=False), patch(
            "combat.combat_utils.apply_attack_power",
            side_effect=lambda w, d: d,
        ), patch("combat.combat_utils.apply_lifesteal"):
            BareHand().at_attack(self.char1, self.char2)

        self._expect_no_condition_message(self.char2)

    def test_melee_weapon_condition(self):
        weapon = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="sword", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.db.dmg = 1
        self.char2.at_damage = self._simple_damage

        with patch("world.system.stat_manager.check_hit", return_value=True), patch(
            "combat.combat_utils.roll_evade",
            return_value=False,
        ), patch("combat.combat_utils.roll_parry", return_value=False), patch(
            "combat.combat_utils.roll_block",
            return_value=False,
        ), patch("world.system.stat_manager.roll_crit", return_value=False), patch(
            "combat.combat_utils.apply_attack_power",
            side_effect=lambda w, d: d,
        ), patch("combat.combat_utils.apply_lifesteal"):
            weapon.at_attack(self.char1, self.char2)

        self._expect_no_condition_message(self.char2)

