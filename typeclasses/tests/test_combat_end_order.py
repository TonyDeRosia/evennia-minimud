from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from combat.round_manager import CombatRoundManager, CombatInstance
from typeclasses.characters import NPC
from typeclasses.tests.test_combat_engine import KillAction


class TestCombatEndOrder(EvenniaTest):
    def test_death_hooks_fire_before_combat_end(self):
        room = self.room1
        player = self.char1
        player.location = room
        npc = create.create_object(NPC, key="mob", location=room)
        npc.db.drops = []
        npc.db.exp_reward = 5

        manager = CombatRoundManager.get()
        manager.force_end_all_combat()
        with patch.object(CombatInstance, "start"):
            instance = manager.start_combat([player, npc])
        engine = instance.engine
        engine.queue_action(player, KillAction(player, npc))

        order = []

        def player_msg(msg, *args, **kwargs):
            if "experience points" in msg:
                order.append(("xp", instance.combat_ended))

        def room_msg(msg, *args, **kwargs):
            if "slain" in msg or "dies" in msg:
                order.append(("death", instance.combat_ended))

        player.msg = MagicMock(side_effect=player_msg)
        room.msg_contents = MagicMock(side_effect=room_msg)

        from world.mechanics import on_death_manager
        orig_handle = on_death_manager.handle_death

        def wrapped_handle(victim, killer=None):
            order.append(("handle", instance.combat_ended))
            return orig_handle(victim, killer)

        corpse = create.create_object("typeclasses.objects.Object", key="corpse", location=None)

        with (
            patch("world.mechanics.on_death_manager.handle_death", side_effect=wrapped_handle),
            patch("world.mechanics.death_handlers.spawn_corpse", return_value=corpse),
            patch("combat.engine.damage_processor.delay"),
            patch("world.system.state_manager.apply_regen"),
            patch("world.system.state_manager.check_level_up"),
            patch("random.randint", return_value=0),
        ):
            engine.start_round()
            engine.process_round()

        assert instance.combat_ended
        for _, ended in order:
            assert not ended
