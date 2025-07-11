from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.npcs import BaseNPC
from commands.combat import CombatCmdSet
from combat.round_manager import CombatInstance


@override_settings(DEFAULT_HOME=None)
class TestAttackCommand(EvenniaTest):
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

    def test_attack_ambiguous_names_auto_selects_first(self):
        slime1 = create.create_object(BaseNPC, key="slime", location=self.room1)
        slime2 = create.create_object(BaseNPC, key="slime", location=self.room1)

        self.char1.execute_cmd("attack slime")
        self.assertEqual(self.char1.db.combat_target, slime1)

        self.char1.execute_cmd("attack slime-2")
        self.assertEqual(self.char1.db.combat_target, slime2)

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

    def test_attack_clears_target_fleeing(self):
        """Attacking a fleeing mob should clear its fleeing flag."""
        mob = create.create_object(BaseNPC, key="mob", location=self.room1)
        mob.db.fleeing = True

        self.char1.execute_cmd("attack mob")

        self.assertFalse(mob.attributes.has("fleeing"))

    def test_attack_corpse_is_blocked(self):
        corpse = create.create_object(
            "typeclasses.objects.Corpse", key="corpse", location=self.room1
        )
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("attack corpse")
        self.assertTrue(self.char1.msg.called)
        out = self.char1.msg.call_args[0][0]
        self.assertIn("can't attack", out)
        from combat.round_manager import CombatRoundManager

        manager = CombatRoundManager.get()
        self.assertFalse(manager.combats)

    def test_joining_combat_queues_immediately(self):
        """Joining an ongoing fight should allow immediate actions."""
        from typeclasses.characters import PlayerCharacter
        from combat.round_manager import CombatRoundManager
        from combat.combat_actions import AttackAction

        with patch.object(CombatInstance, "start"):
            self.char1.execute_cmd("attack char2")

        char3 = create.create_object(
            PlayerCharacter,
            key="Char3",
            location=self.room1,
            home=self.room1,
        )
        char3.msg = MagicMock()
        char3.cmdset.add_default(CombatCmdSet)

        with patch.object(CombatInstance, "start"):
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
