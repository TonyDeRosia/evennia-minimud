"""Tests for attack and kill commands.

The :class:`TestAttackCommand` suite verifies that issuing ``attack`` or
its ``kill``/``k`` aliases correctly initiates combat, queues actions and
handles joining ongoing fights.
"""

from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils import create
from .base import AttackCommandTestBase
from typeclasses.npcs import BaseNPC
from commands.combat import CombatCmdSet


@override_settings(DEFAULT_HOME=None)
class TestAttackCommand(AttackCommandTestBase):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(CombatCmdSet)

    def test_attack_without_can_attack(self):
        mob = create.create_object(BaseNPC, key="mob", location=self.room1)
        self.char1.execute_cmd("attack mob")
        self.assertEqual(self.char1.db.combat_target, mob)
        self.assertEqual(mob.db.combat_target, self.char1)

        from combat.round_manager import CombatRoundManager
        from combat.combat_actions import AttackAction

        manager = CombatRoundManager.get()
        self.assertTrue(manager.combats)
        engine = list(manager.combats.values())[0].engine
        queued = any(
            isinstance(act, AttackAction)
            for p in engine.participants
            for act in p.next_action
        )
        self.assertTrue(queued)

    def test_attack_when_not_fleeing(self):
        """Attacking without a fleeing flag should not raise errors."""
        mob = create.create_object(BaseNPC, key="mob", location=self.room1)
        # ensure the fleeing attribute is not present
        if self.char1.attributes.has("fleeing"):
            self.char1.attributes.remove("fleeing")

        # should not raise when no fleeing attribute exists
        self.char1.execute_cmd("attack mob")

        # fleeing flag should still be absent after attacking
        self.assertFalse(self.char1.attributes.has("fleeing"))

    def test_joining_combat_queues_immediately(self):
        """Joining an ongoing fight should allow immediate actions."""
        from typeclasses.characters import PlayerCharacter
        from combat.round_manager import CombatRoundManager
        from combat.combat_actions import AttackAction

        with patch("combat.round_manager.delay"):
            self.char1.execute_cmd("attack char2")

        char3 = create.create_object(
            PlayerCharacter,
            key="Char3",
            location=self.room1,
            home=self.room1,
        )
        char3.msg = MagicMock()
        char3.cmdset.add_default(CombatCmdSet)

        with patch("combat.round_manager.delay"):
            char3.execute_cmd("attack char2")

        manager = CombatRoundManager.get()
        engine = list(manager.combats.values())[0].engine

        self.assertIn(char3, [p.actor for p in engine.participants])
        queued = [
            act
            for p in engine.participants
            if p.actor is char3
            for act in p.next_action
            if isinstance(act, AttackAction)
        ]
        self.assertTrue(queued)

    def test_kill_alias_starts_combat(self):
        """Using the kill alias should initiate combat like attack."""
        mob = create.create_object(BaseNPC, key="mob", location=self.room1)
        self.char1.execute_cmd("kill mob")

        self._assert_combat_targets_set(self.char1, mob)
        self._assert_combat_initiated()

    @patch("combat.round_manager.delay")
    def test_kill_alias_with_character_target(self, _):
        """Issuing 'kill char2' should start combat and set targets."""
        self.char1.execute_cmd("kill char2")

        self._assert_combat_targets_set(self.char1, self.char2)
        self._assert_combat_initiated()

    @patch("combat.round_manager.delay")
    def test_kill_and_attack_equivalence(self, _):
        """Using attack and kill should result in the same combat state."""
        # First start combat using attack
        self.char1.execute_cmd("attack char2")
        from combat.round_manager import CombatRoundManager

        manager = CombatRoundManager.get()
        engine = list(manager.combats.values())[0].engine
        participants_attack = {p.actor for p in engine.participants}
        queued_attack = {
            p.actor: [type(a) for a in p.next_action]
            for p in engine.participants
        }

        # reset combat
        manager.combats.clear()
        manager.combatant_to_combat.clear()
        self.char1.db.combat_target = None
        self.char2.db.combat_target = None

        # Start combat again using kill
        self.char1.execute_cmd("kill char2")
        engine2 = list(manager.combats.values())[0].engine
        participants_kill = {p.actor for p in engine2.participants}
        queued_kill = {
            p.actor: [type(a) for a in p.next_action]
            for p in engine2.participants
        }

        self.assertEqual(participants_attack, participants_kill)
        self.assertEqual(queued_attack, queued_kill)
        self._assert_combat_targets_set(self.char1, self.char2)
        self._assert_combat_initiated()

    @patch("combat.round_manager.delay")
    def test_k_short_alias_initiates_combat(self, _):
        """The short 'k' alias should behave the same as kill."""
        self.char1.execute_cmd("k char2")

        self._assert_combat_targets_set(self.char1, self.char2)
        self._assert_combat_initiated()

    @patch("combat.round_manager.delay")
    def test_attack_separator_variants(self, _):
        """Separators 'with', 'w' and 'w/' should all parse correctly."""
        weapon = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="sword", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")

        for sep in ("with", "w", "w/"):
            cmd = f"attack char2 {sep} sword"
            self.char1.execute_cmd(cmd)
            self._assert_combat_targets_set(self.char1, self.char2)
            self._assert_combat_initiated(actor=self.char1)

            from combat.round_manager import CombatRoundManager

            manager = CombatRoundManager.get()
            manager.combats.clear()
            manager.combatant_to_combat.clear()
            self.char1.db.combat_target = None
            self.char2.db.combat_target = None

    @patch("combat.round_manager.delay")
    def test_attack_uses_returned_instance(self, _):
        """Attack command should use the instance returned by start_or_get_combat."""
        mock_engine = MagicMock()
        inst = MagicMock(engine=mock_engine, combatants={self.char1, self.char2})
        with patch(
            "commands.combat.start_or_get_combat", return_value=inst
        ) as mock_start, patch("commands.combat.CombatRoundManager.get") as mock_get, patch(
            "commands.combat.AttackAction"
        ):
            manager = MagicMock()
            mock_get.return_value = manager
            manager.get_combatant_combat.return_value = None

            self.char1.execute_cmd("attack char2")

            mock_start.assert_called_with(self.char1, self.char2)
            mock_engine.queue_action.assert_called()

