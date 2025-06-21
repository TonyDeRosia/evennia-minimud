import unittest
from unittest.mock import patch, MagicMock

from combat.round_manager import CombatRoundManager, CombatInstance
from combat.engine import CombatEngine

class Dummy:
    def __init__(self, hp=10):
        self.hp = hp
        self.location = MagicMock()
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=0)
        self.traits.health = MagicMock(value=hp, max=hp)
        self.db = type("DB", (), {"temp_bonuses": {}, "experience": 0, "tnl": 0, "level": 1})()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.msg = MagicMock()

class UnsavedDummy(Dummy):
    class FakeDB:
        def __setattr__(self, name, value):
            raise AttributeError("unsaved object")

    def __init__(self, hp=10):
        super().__init__(hp)
        self.pk = None
        self.db = self.FakeDB()

class TestUnsavedRoundManager(unittest.TestCase):
    def test_unsaved_fighter_keeps_combat_alive(self):
        player = Dummy()
        npc = UnsavedDummy()
        manager = CombatRoundManager.get()
        manager.combats.clear()
        manager.combatant_to_combat.clear()
        with patch.object(CombatInstance, "_schedule_tick"), patch.object(CombatEngine, "process_round"):
            inst = manager.create_combat([player, npc])
            inst._tick()
        self.assertFalse(inst.combat_ended)
        self.assertTrue(getattr(npc, "in_combat", False))


class TestUnsavedAttackerDamage(unittest.TestCase):
    def test_unsaved_attacker_damage_logging(self):
        from typeclasses.characters import Character

        class Victim:
            def __init__(self, hp=10):
                self.traits = type("Traits", (), {})()
                self.traits.health = type("Health", (), {"current": hp, "value": hp})()
                self.ndb = type("NDB", (), {})()
                self.msg = MagicMock()
                self.db = type("DB", (), {"bounty": 0})()

            def defense(self, dt=None):
                return 0

        player = Victim()
        npc = UnsavedDummy()
        npc.get_display_name = lambda looker=None: "NPC"

        manager = CombatRoundManager.get()
        manager.combats.clear()
        manager.combatant_to_combat.clear()

        with patch.object(CombatInstance, "start"):
            manager.create_combat([player, npc])

        with patch("world.system.state_manager.get_effective_stat", return_value=0):
            Character.at_damage(player, npc, 5)

        self.assertEqual(player.ndb.damage_log.get(id(npc)), 5)
