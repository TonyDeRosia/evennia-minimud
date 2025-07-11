import unittest
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from combat.combat_actions import Action, CombatResult
from combat.round_manager import CombatRoundManager, CombatInstance


class DamageAction(Action):
    """Simple action that deals a fixed amount of damage."""

    def __init__(self, actor, target, damage=1):
        super().__init__(actor, target)
        self.damage = damage

    def resolve(self):
        return CombatResult(self.actor, self.target, "hit", damage=self.damage)


class TestCombatFullFight(EvenniaTest):
    def test_fight_runs_until_defeat(self):
        with patch.object(CombatInstance, "start"):
            manager = CombatRoundManager.get()
            instance = manager.start_combat([self.char1, self.char2])
            engine = instance.engine

            # give both characters small amounts of health
            self.char1.hp = self.char1.traits.health.value = 4
            self.char2.hp = self.char2.traits.health.value = 4

            engine.queue_action(self.char1, DamageAction(self.char1, self.char2, 2))
            engine.queue_action(self.char2, DamageAction(self.char2, self.char1, 1))

            rounds = 0
            with patch("world.system.state_manager.apply_regen"), patch(
                "random.randint", return_value=0
            ):
                while self.char1.hp > 0 and self.char2.hp > 0:
                    instance.process_round()
                    rounds += 1
                    self.assertFalse(instance.combat_ended)
                    if self.char1.hp > 0 and self.char2.hp > 0:
                        engine.queue_action(
                            self.char1, DamageAction(self.char1, self.char2, 2)
                        )
                        engine.queue_action(
                            self.char2, DamageAction(self.char2, self.char1, 1)
                        )

            self.assertTrue(self.char1.hp == 0 or self.char2.hp == 0)
            self.assertGreater(rounds, 0)
