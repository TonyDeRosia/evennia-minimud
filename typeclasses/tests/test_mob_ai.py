import unittest
from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings

from world.npc_handlers import mob_ai
from scripts.global_npc_ai import GlobalNPCAI
from combat.ai_combat import auto_attack


@override_settings(DEFAULT_HOME=None)
class TestMobAIScript(EvenniaTest):
    def test_script_calls_mob_ai(self):
        from scripts.global_npc_ai import GlobalNPCAI
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="mob", location=self.room1)
        npc.db.ai_type = "aggressive"
        npc.tags.add("npc_ai")
        script = GlobalNPCAI()

        with patch("scripts.global_npc_ai.process_mob_ai") as mock_proc:
            script.at_repeat()
            mock_proc.assert_called_with(npc)


@override_settings(DEFAULT_HOME=None)
class TestMobAIBehaviors(EvenniaTest):
    def test_scavenger_picks_up_valuable_item(self):
        from typeclasses.npcs import BaseNPC
        from typeclasses.objects import Object

        npc = create.create_object(BaseNPC, key="scav", location=self.room1)
        npc.db.actflags = ["scavenger"]
        item1 = create.create_object(Object, key="cheap", location=self.room1)
        item1.db.value = 1
        item2 = create.create_object(Object, key="rich", location=self.room1)
        item2.db.value = 5

        mob_ai.process_mob_ai(npc)
        self.assertEqual(item2.location, npc)
        self.assertEqual(item1.location, self.room1)

    def test_aggressive_attacks_player(self):
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="orc", location=self.room1)
        npc.db.actflags = ["aggressive"]
        with patch.object(npc, "enter_combat") as mock:
            mob_ai.process_mob_ai(npc)
            mock.assert_called_with(self.char1)

    def test_aggressive_flag_spawns_script_and_attacks(self):
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="flag", location=self.room1)
        npc.db.actflags = ["aggressive"]
        npc.at_object_creation()

        self.assertTrue(npc.tags.get("npc_ai"))
        script = GlobalNPCAI()

        with patch.object(npc, "enter_combat") as mock:
            script.at_repeat()
            mock.assert_called_with(self.char1)

    def test_memory_attack(self):
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="ogre", location=self.room1)
        mob_ai.remember(npc, self.char1)
        with patch.object(npc, "enter_combat") as mock:
            mob_ai.process_mob_ai(npc)
            mock.assert_called_with(self.char1)

    def test_assist_allies(self):
        from typeclasses.npcs import BaseNPC
        from combat.round_manager import CombatRoundManager

        ally = create.create_object(BaseNPC, key="ally", location=self.room1, home=self.room1)
        ally.db.ai_type = "defensive"
        ally.db.actflags = []
        manager = CombatRoundManager.get()
        instance = manager.start_combat([ally, self.char1])
        ally.db.combat_target = self.char1
        self.char1.db.combat_target = ally

        helper = create.create_object(BaseNPC, key="helper", location=self.room1, home=self.room1)
        helper.db.auto_assist = True

        with patch.object(helper, "enter_combat") as mock, patch("world.npc_handlers.mob_ai._call_for_help"):
            mob_ai.process_mob_ai(helper)
            mock.assert_called_with(self.char1)

    def test_no_auto_assist_no_join(self):
        from typeclasses.npcs import BaseNPC
        from combat.round_manager import CombatRoundManager

        ally = create.create_object(BaseNPC, key="ally2", location=self.room1, home=self.room1)
        manager = CombatRoundManager.get()
        manager.start_combat([ally, self.char1])
        ally.db.combat_target = self.char1
        self.char1.db.combat_target = ally

        helper = create.create_object(BaseNPC, key="helper2", location=self.room1, home=self.room1)

        with patch.object(helper, "enter_combat") as mock, patch("world.npc_handlers.mob_ai._call_for_help"):
            mob_ai.process_mob_ai(helper)
            mock.assert_not_called()

    def test_player_auto_assist(self):
        from typeclasses.npcs import BaseNPC
        from combat.round_manager import CombatRoundManager

        ally = create.create_object(BaseNPC, key="pally", location=self.room1, home=self.room1)
        manager = CombatRoundManager.get()
        manager.start_combat([ally, self.char2])
        ally.db.combat_target = self.char2
        self.char2.db.combat_target = ally

        from typeclasses.characters import PlayerCharacter

        player = create.create_object(PlayerCharacter, key="assist", location=self.room1, home=self.room1)
        player.db.auto_assist = True
        player.enter_combat = MagicMock()

        mob_ai._assist_allies(player)
        player.enter_combat.assert_called_with(self.char2)

    def test_wander_moves(self):
        from typeclasses.npcs import BaseNPC
        from typeclasses.exits import Exit

        dest = create.create_object("typeclasses.rooms.Room", key="dest")
        exit_obj = create.create_object(Exit, key="east", location=self.room1)
        exit_obj.destination = dest
        npc = create.create_object(BaseNPC, key="walker", location=self.room1)
        npc.db.actflags = ["wander"]

        with patch.object(exit_obj, "at_traverse") as mock:
            mob_ai.process_mob_ai(npc)
            mock.assert_called_with(npc, dest)

    def test_no_wander_no_move(self):
        from typeclasses.npcs import BaseNPC
        from typeclasses.exits import Exit

        dest = create.create_object("typeclasses.rooms.Room", key="dest")
        exit_obj = create.create_object(Exit, key="east", location=self.room1)
        exit_obj.destination = dest
        npc = create.create_object(BaseNPC, key="idler", location=self.room1)

        with patch.object(exit_obj, "at_traverse") as mock:
            mob_ai.process_mob_ai(npc)
            mock.assert_not_called()

    def test_stay_area_blocks_travel(self):
        from typeclasses.npcs import BaseNPC
        from typeclasses.exits import Exit

        dest = create.create_object("typeclasses.rooms.Room", key="far")
        dest.db.area = "elsewhere"
        exit_obj = create.create_object(Exit, key="east", location=self.room1)
        exit_obj.destination = dest
        self.room1.db.area = "home"

        npc = create.create_object(BaseNPC, key="homebody", location=self.room1)
        npc.db.actflags = ["wander", "stay_area"]
        npc.db.area_tag = "home"

        with patch.object(exit_obj, "at_traverse") as mock:
            mob_ai.process_mob_ai(npc)
            mock.assert_not_called()

    def test_call_for_help_summons_allies(self):
        from typeclasses.npcs import BaseNPC
        from combat.round_manager import CombatRoundManager

        caller = create.create_object(BaseNPC, key="caller", location=self.room1)
        caller.db.actflags = ["call_for_help"]
        manager = CombatRoundManager.get()
        manager.start_combat([caller, self.char1])

        ally = create.create_object(BaseNPC, key="ally", location=self.room1)
        ally.db.actflags = ["assist"]

        self.room1.msg_contents = MagicMock()

        with patch.object(ally, "enter_combat") as mock:
            mob_ai.process_mob_ai(caller)
            mock.assert_called_with(self.char1)
            self.assertTrue(caller.ndb.called_for_help)

        self.room1.msg_contents.reset_mock()
        with patch.object(ally, "enter_combat") as mock:
            mob_ai.process_mob_ai(caller)
            mock.assert_not_called()
        self.assertFalse(self.room1.msg_contents.called)

    def test_wimpy_flees_when_low_hp(self):
        from typeclasses.npcs import BaseNPC
        from combat.round_manager import CombatRoundManager

        npc = create.create_object(BaseNPC, key="coward", location=self.room1)
        npc.db.actflags = ["wimpy"]
        npc.hp = 20
        npc.max_hp = 100
        manager = CombatRoundManager.get()
        manager.start_combat([npc, self.char1])

        npc.execute_cmd = MagicMock()

        mob_ai.process_mob_ai(npc)

        npc.execute_cmd.assert_called_with("flee")

    def test_wimpy_uses_custom_threshold(self):
        """NPC flees when HP is below its custom ``flee_at`` value."""
        from typeclasses.npcs import BaseNPC
        from combat.round_manager import CombatRoundManager

        npc = create.create_object(BaseNPC, key="scared", location=self.room1)
        npc.db.actflags = ["wimpy"]
        npc.db.flee_at = 50
        npc.hp = 40
        npc.max_hp = 100
        manager = CombatRoundManager.get()
        manager.start_combat([npc, self.char1])

        npc.execute_cmd = MagicMock()

        mob_ai.process_mob_ai(npc)

        npc.execute_cmd.assert_called_with("flee")

    def test_wimpy_stays_above_custom_threshold(self):
        """NPC does not flee if current HP is above ``flee_at``."""
        from typeclasses.npcs import BaseNPC
        from combat.round_manager import CombatRoundManager

        npc = create.create_object(BaseNPC, key="brave", location=self.room1)
        npc.db.actflags = ["wimpy"]
        npc.db.flee_at = 50
        npc.hp = 80
        npc.max_hp = 100
        manager = CombatRoundManager.get()
        manager.start_combat([npc, self.char1])

        npc.execute_cmd = MagicMock()

        mob_ai.process_mob_ai(npc)

        npc.execute_cmd.assert_not_called()

    def test_helper_auto_attacks_when_ally_attacked(self):
        from typeclasses.npcs import BaseNPC
        from combat.round_manager import CombatRoundManager, CombatInstance

        manager = CombatRoundManager.get()
        manager.combats.clear()
        manager.combatant_to_combat.clear()

        ally = create.create_object(BaseNPC, key="assist_target", location=self.room1, home=self.room1)

        with patch.object(CombatInstance, "start"):
            instance = manager.start_combat([ally, self.char1])

            ally.db.combat_target = self.char1
            self.char1.db.combat_target = ally

            helper = create.create_object(BaseNPC, key="helper", location=self.room1, home=self.room1)
            helper.db.auto_assist = True

            with patch.object(helper, "attack") as mock_attack, \
                 patch("combat.ai_combat.auto_attack", wraps=auto_attack) as mock_auto, \
                 patch.object(helper, "enter_combat", wraps=helper.enter_combat) as mock_enter, \
                 patch("world.npc_handlers.mob_ai._call_for_help"):
                mob_ai.process_mob_ai(helper)
                mock_enter.assert_called_with(self.char1)
                self.assertTrue(helper.in_combat)

                instance._manual_round_processing()

                mock_auto.assert_called_with(helper)
                mock_attack.assert_called()
