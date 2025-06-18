import unittest

from combat.round_manager import CombatRoundManager, CombatInstance
from combat.combat_states import CombatStateManager, CombatState

class DummyObj:
    def __init__(self):
        self.pk = None
        self.saved = False
        self.hp = 10
        self.db = type("DB", (), {})()
    def save(self):
        self.pk = id(self)
        self.saved = True

class DummyFailObj(DummyObj):
    def save(self):
        raise RuntimeError("boom")

class DummyEngine:
    def __init__(self):
        self.participants = []
    def add_participant(self, obj):
        self.participants.append(type("P", (), {"actor": obj}))

class SaveTests(unittest.TestCase):
    def setUp(self):
        CombatRoundManager._instance = None
        self.manager = CombatRoundManager.get()
        # avoid scheduling tasks during tests
        self._orig_start = CombatInstance.start
        CombatInstance.start = lambda self: None

    def tearDown(self):
        self.manager.force_end_all_combat()
        CombatRoundManager._instance = None
        CombatInstance.start = self._orig_start

    def test_add_combatant_saves_unsaved_obj(self):
        obj = DummyObj()
        inst = CombatInstance(1, DummyEngine(), set(), 1.0)
        inst.add_combatant(obj)
        self.assertTrue(obj.saved)
        self.assertIn(obj, inst.combatants)

    def test_create_combat_saves_combatants(self):
        a = DummyObj()
        b = DummyObj()
        inst = self.manager.create_combat([a, b])
        self.assertTrue(a.saved)
        self.assertTrue(b.saved)
        self.assertEqual(self.manager.combatant_to_combat[a], inst.combat_id)
        self.assertEqual(self.manager.combatant_to_combat[b], inst.combat_id)

    def test_start_combat_saves_new_combatants_before_add(self):
        a = DummyObj()
        self.manager.create_combat([a])
        b = DummyObj()
        added_saved = {}
        orig_add = CombatInstance.add_combatant
        def patched(self, obj, **kwargs):
            added_saved['flag'] = obj.saved
            return orig_add(self, obj, **kwargs)
        CombatInstance.add_combatant = patched
        self.manager.start_combat([a, b])
        CombatInstance.add_combatant = orig_add
        self.assertTrue(added_saved.get('flag'))

class StateManagerTests(unittest.TestCase):
    def test_add_state_saves_object_or_skips(self):
        mgr = CombatStateManager()
        state = CombatState(key="test", duration=5)
        obj = DummyObj()
        mgr.add_state(obj, state)
        self.assertTrue(obj.saved)
        self.assertIn(obj, mgr.states)

        obj2 = DummyFailObj()
        mgr.add_state(obj2, state)
        self.assertNotIn(obj2, mgr.states)

if __name__ == "__main__":
    unittest.main()
