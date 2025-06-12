from unittest.mock import MagicMock
from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.npcs import BaseNPC
from commands.combat import CombatCmdSet


@override_settings(DEFAULT_HOME=None)
class TestAttackCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.attack = MagicMock()
        self.char1.cmdset.add_default(CombatCmdSet)

    def test_attack_without_can_attack(self):
        mob = create.create_object(BaseNPC, key="mob", location=self.room1)
        self.char1.execute_cmd("attack mob")
        self.assertEqual(self.char1.db.combat_target, mob)
        self.char1.attack.assert_called()
