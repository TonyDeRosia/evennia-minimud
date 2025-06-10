import unittest
from combat.combat_states import CombatState, CombatStateManager


class Dummy:
    pass


class TestCombatStates(unittest.TestCase):
    def test_stacking_and_diminish(self):
        mgr = CombatStateManager()
        obj = Dummy()
        base = CombatState(key="bleeding", duration=4, max_stacks=3, diminish=0.5)
        mgr.add_state(obj, base)
        self.assertEqual(mgr.states[obj]["bleeding"].duration, 4)
        self.assertEqual(mgr.states[obj]["bleeding"].stacks, 1)

        mgr.add_state(obj, CombatState(key="bleeding", duration=4, max_stacks=3, diminish=0.5))
        self.assertEqual(mgr.states[obj]["bleeding"].stacks, 2)
        self.assertEqual(mgr.states[obj]["bleeding"].duration, 6)

        mgr.add_state(obj, CombatState(key="bleeding", duration=4, max_stacks=3, diminish=0.5))
        self.assertEqual(mgr.states[obj]["bleeding"].stacks, 3)
        self.assertEqual(mgr.states[obj]["bleeding"].duration, 7)

        mgr.add_state(obj, CombatState(key="bleeding", duration=4, max_stacks=3, diminish=0.5))
        self.assertEqual(mgr.states[obj]["bleeding"].stacks, 3)
        self.assertEqual(mgr.states[obj]["bleeding"].duration, 8)

    def test_callbacks(self):
        events = []

        def on_apply(o, s):
            events.append("apply")

        def on_tick(o, s):
            events.append("tick")

        def on_expire(o, s):
            events.append("expire")

        mgr = CombatStateManager()
        obj = Dummy()
        state = CombatState(
            key="bleeding",
            duration=1,
            on_apply=on_apply,
            on_tick=on_tick,
            on_expire=on_expire,
        )
        mgr.add_state(obj, state)
        mgr.tick()

        self.assertEqual(events, ["apply", "tick", "expire"])

