from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from combat.engine import CombatEngine
from typeclasses.characters import NPC
from typeclasses.tests.test_combat_engine import KillAction


class TestDamageProcessorHandleDefeat(EvenniaTest):
    def test_npc_death_removes_and_broadcasts(self):
        room = self.room1
        player = self.char1
        npc = create.create_object(NPC, key="mob", location=room)
        npc.db.drops = []
        room.msg_contents = MagicMock()

        engine = CombatEngine([player, npc], round_time=0)
        engine.queue_action(player, KillAction(player, npc))

        with patch("world.system.state_manager.apply_regen"), patch(
            "world.system.state_manager.check_level_up"
        ), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        self.assertNotIn(npc, room.contents)
        corpse = next(
            obj for obj in room.contents if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        )
        self.assertIsNotNone(corpse)
        calls = [c.args[0] for c in room.msg_contents.call_args_list]
        self.assertTrue(any("slain" in msg for msg in calls))
