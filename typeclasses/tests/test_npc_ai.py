from unittest.mock import patch, MagicMock
from django.test import override_settings

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestGlobalNPCAI(EvenniaTest):
    def test_script_calls_process_ai(self):
        from scripts.global_npc_ai import GlobalNPCAI
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="mob", location=self.room1)
        npc.db.ai_type = "aggressive"
        npc.tags.add("npc_ai")
        script = GlobalNPCAI()

        with patch("scripts.global_npc_ai.process_mob_ai") as mock_proc:
            script.at_repeat()
            mock_proc.assert_called_with(npc)

    def test_base_npc_tagged_for_ai(self):
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="mob2", location=self.room1)
        npc.db.ai_type = "passive"
        npc.at_object_creation()
        self.assertTrue(npc.tags.get("npc_ai"))

    def test_scripted_ai_string_callback(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="mob3", location=self.room1)
        npc.db.ai_type = "scripted"
        npc.db.ai_script = "scripts.example_ai.patrol_ai"

        with patch("scripts.example_ai.patrol_ai") as mock_call:
            ai.process_ai(npc)
            mock_call.assert_called_with(npc)

    def test_scripted_ai_direct_callable(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        called = {}

        def callback(obj):
            called["ran"] = obj

        npc = create.create_object(BaseNPC, key="mob4", location=self.room1)
        npc.db.ai_type = "scripted"
        npc.db.ai_script = callback

        ai.process_ai(npc)
        self.assertIs(called.get("ran"), npc)

    def test_wanderer_defaults_to_wander_ai(self):
        from typeclasses.npcs import WandererNPC

        npc = create.create_object(WandererNPC, key="wander", location=self.room1)
        npc.at_object_creation()

        self.assertEqual(npc.db.ai_type, "wander")
        self.assertTrue(npc.tags.get("npc_ai"))



@override_settings(DEFAULT_HOME=None)
class TestAIBehaviors(EvenniaTest):
    def test_aggressive_ai_enters_combat(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="agg", location=self.room1)
        npc.db.ai_type = "aggressive"
        with patch.object(npc, "enter_combat") as mock:
            ai.process_ai(npc)
            mock.assert_called()

    def test_defensive_ai_attacks_only_in_combat(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="def", location=self.room1)
        npc.db.ai_type = "defensive"
        npc.in_combat = False
        with patch.object(npc, "attack") as mock:
            ai.process_ai(npc)
            mock.assert_not_called()
        npc.in_combat = True
        npc.db.combat_target = self.char1
        with patch.object(npc, "attack") as mock:
            ai.process_ai(npc)
            mock.assert_called_with(self.char1, npc)

    def test_wander_ai_moves(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC
        from typeclasses.exits import Exit

        dest = create.create_object("typeclasses.rooms.Room", key="dest")
        exit_obj = create.create_object(Exit, key="east", location=self.room1)
        exit_obj.destination = dest
        npc = create.create_object(BaseNPC, key="wander", location=self.room1)
        npc.db.ai_type = "wander"
        with patch.object(exit_obj, "at_traverse") as mock:
            ai.process_ai(npc)
            mock.assert_called_with(npc, dest)

    def test_wander_ai_sentinel_does_not_move(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC
        from typeclasses.exits import Exit

        dest = create.create_object("typeclasses.rooms.Room", key="dest")
        exit_obj = create.create_object(Exit, key="east", location=self.room1)
        exit_obj.destination = dest
        npc = create.create_object(BaseNPC, key="sentinel", location=self.room1)
        npc.db.ai_type = "wander"
        npc.db.actflags = ["sentinel"]

        with patch.object(exit_obj, "at_traverse") as mock:
            ai.process_ai(npc)
            mock.assert_not_called()

    def test_invalid_ai_type_no_action(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="none", location=self.room1)
        npc.db.ai_type = "bogus"
        with patch.object(npc, "attack") as mock:
            ai.process_ai(npc)
            mock.assert_not_called()

    def test_assist_flag_attacks_leader_target(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="helper", location=self.room1)
        npc.db.ai_type = "passive"
        npc.db.actflags = ["assist"]
        npc.db.following = self.char1

        self.char1.location = self.room1
        from combat.round_manager import CombatRoundManager
        manager = CombatRoundManager.get()
        manager.start_combat([self.char1, self.char2])

        with patch.object(npc, "enter_combat") as mock:
            ai.process_ai(npc)
            mock.assert_called_with(self.char2)

    def test_call_for_help_summons_allies(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        caller = create.create_object(BaseNPC, key="caller", location=self.room1)
        caller.db.ai_type = "defensive"
        caller.db.actflags = ["call_for_help"]
        from combat.round_manager import CombatRoundManager
        manager = CombatRoundManager.get()
        manager.start_combat([caller, self.char1])

        ally = create.create_object(BaseNPC, key="ally", location=self.room1)
        ally.db.ai_type = "passive"
        ally.db.actflags = ["assist"]

        self.room1.msg_contents = MagicMock()

        with patch.object(ally, "enter_combat") as mock:
            ai.process_ai(caller)
            mock.assert_called_with(self.char1)
        self.assertTrue(self.room1.msg_contents.called)

    def test_finalize_adds_ai_tag_and_auto_attacks(self):
        from commands import npc_builder
        from typeclasses.npcs import BaseNPC
        from scripts.global_npc_ai import GlobalNPCAI

        npc = create.create_object(BaseNPC, key="attacker", location=self.room1)
        npc.db.level = 1
        npc.db.combat_class = "Warrior"
        npc.db.ai_type = "aggressive"

        npc_builder.finalize_mob_prototype(self.char1, npc)

        self.assertTrue(npc.tags.get("npc_ai"))

        self.char1.location = self.room1
        script = GlobalNPCAI()

        with patch.object(npc, "enter_combat") as mock:
            script.at_repeat()
            mock.assert_called_with(self.char1)
