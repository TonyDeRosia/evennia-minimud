import unittest
from combat.effects import StatusEffect, EffectManager


class Dummy:
    pass


class TestCombatStates(unittest.TestCase):
    def test_stacking_and_diminish(self):
        mgr = EffectManager()
        obj = Dummy()
        base = StatusEffect(key="bleeding", duration=4, max_stacks=3, diminish=0.5)
        mgr.add_effect(obj, base)
        self.assertEqual(mgr.effects[obj]["bleeding"].duration, 4)
        self.assertEqual(mgr.effects[obj]["bleeding"].stacks, 1)

        mgr.add_effect(obj, StatusEffect(key="bleeding", duration=4, max_stacks=3, diminish=0.5))
        self.assertEqual(mgr.effects[obj]["bleeding"].stacks, 2)
        self.assertEqual(mgr.effects[obj]["bleeding"].duration, 6)

        mgr.add_effect(obj, StatusEffect(key="bleeding", duration=4, max_stacks=3, diminish=0.5))
        self.assertEqual(mgr.effects[obj]["bleeding"].stacks, 3)
        self.assertEqual(mgr.effects[obj]["bleeding"].duration, 7)

        mgr.add_effect(obj, StatusEffect(key="bleeding", duration=4, max_stacks=3, diminish=0.5))
        self.assertEqual(mgr.effects[obj]["bleeding"].stacks, 3)
        self.assertEqual(mgr.effects[obj]["bleeding"].duration, 8)

    def test_callbacks(self):
        events = []

        def on_apply(o, s):
            events.append("apply")

        def on_tick(o, s):
            events.append("tick")

        def on_expire(o, s):
            events.append("expire")

        mgr = EffectManager()
        obj = Dummy()
        state = StatusEffect(
            key="bleeding",
            duration=1,
            on_apply=on_apply,
            on_tick=on_tick,
            on_expire=on_expire,
        )
        mgr.add_effect(obj, state)
        mgr.tick()

        self.assertEqual(events, ["apply", "tick", "expire"])

    def test_states_removed_when_object_deleted(self):
        mgr = EffectManager()
        obj = Dummy()
        mgr.add_effect(obj, StatusEffect(key="bleeding", duration=1))
        self.assertIn(obj, mgr.effects)
        del obj
        import gc

        gc.collect()
        self.assertEqual(len(mgr.effects), 0)

