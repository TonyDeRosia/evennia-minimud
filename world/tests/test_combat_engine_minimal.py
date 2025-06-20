import unittest
from unittest.mock import MagicMock, patch

from combat.engine import CombatEngine
from combat.combat_actions import Action, CombatResult


class Dummy:
    def __init__(self, hp=10, initiative=0, key="dummy"):
        self.hp = hp
        self.initiative = initiative
        self.key = key
        self.location = MagicMock()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.at_defeat = MagicMock()
        self.msg = MagicMock()
        self.pk = 1

    def at_damage(self, attacker, amount, damage_type=None):
        self.hp = max(self.hp - amount, 0)
        return amount


class DamageAction(Action):
    def resolve(self):
        return CombatResult(self.actor, self.target, "hit", damage=5)


class KillAction(Action):
    def resolve(self):
        self.target.hp = 0
        return CombatResult(self.actor, self.target, "boom")


class NoOpAction(Action):
    """Action that does nothing, used to suppress default attacks."""

    def resolve(self):
        return CombatResult(self.actor, self.actor, "")


class TestCombatEngineMinimal(unittest.TestCase):
    def test_turn_order_respects_initiative(self):
        fast = Dummy(initiative=10, key="fast")
        slow = Dummy(initiative=1, key="slow")
        engine = CombatEngine([fast, slow], round_time=0)
        with patch("world.system.state_manager.apply_regen"), patch(
            "random.randint", return_value=0
        ):
            engine.start_round()
        self.assertEqual(engine.turn_manager.queue[0].actor, fast)
        self.assertEqual(engine.turn_manager.queue[1].actor, slow)

    def test_damage_application_reduces_hp(self):
        attacker = Dummy(key="attacker")
        defender = Dummy(key="defender")
        room = MagicMock()
        attacker.location = defender.location = room
        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(defender, NoOpAction(defender))
        engine.queue_action(attacker, DamageAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), patch(
            "combat.damage_processor.delay"
        ), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()
        self.assertEqual(defender.hp, 5)

    def test_defeat_removes_participant(self):
        attacker = Dummy(key="attacker")
        defender = Dummy(key="defender")
        room = MagicMock()
        attacker.location = defender.location = room
        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(defender, NoOpAction(defender))
        engine.queue_action(attacker, KillAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), patch(
            "combat.damage_processor.delay"
        ), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()
        participants = [p.actor for p in engine.participants]
        self.assertNotIn(defender, participants)
        defender.on_exit_combat.assert_called()

    def test_action_skipped_if_target_dead(self):
        attacker = Dummy(key="attacker")
        defender = Dummy(hp=0, key="defender")
        room = MagicMock()
        attacker.location = defender.location = room
        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, DamageAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), patch(
            "combat.damage_processor.delay"
        ), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        room.msg_contents.assert_not_called()

    def test_xp_awarded_on_defeat(self):
        attacker = Dummy(key="attacker")
        defender = Dummy(key="defender")

        class XPNPC(Dummy):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.db = type("db", (), {"exp_reward": 5})()
                self.engine = None
                self.drop_loot = MagicMock(return_value=MagicMock(contents=[]))

            def on_death(self, killer):
                self.drop_loot(killer)
                if self.engine:
                    self.engine.award_experience(killer, self)

        defender = XPNPC(key="defender")
        room = MagicMock()
        room.contents = [attacker, defender]
        attacker.location = defender.location = room
        engine = CombatEngine([attacker, defender], round_time=0)
        attacker.engine = engine
        defender.engine = engine
        engine.queue_action(defender, NoOpAction(defender))
        engine.queue_action(attacker, KillAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), patch(
            "combat.damage_processor.delay"
        ), patch("random.randint", return_value=0), patch.object(
            engine, "award_experience"
        ) as mock_xp:
            engine.start_round()
            engine.process_round()

        mock_xp.assert_called_once_with(attacker, defender)

    def test_corpse_spawn_and_loot_drop(self):
        attacker = Dummy(key="attacker")

        loot = object()

        class LootNPC(Dummy):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.loot = [loot]
                self.drop_loot = MagicMock(side_effect=self._drop)

            def _drop(self, killer=None):
                corpse = MagicMock()
                corpse.contents = list(self.loot)
                if self.location:
                    self.location.contents.append(corpse)
                return corpse

            def on_death(self, killer):
                return self.drop_loot(killer)

        defender = LootNPC(key="defender")
        room = MagicMock()
        room.contents = [attacker, defender]
        attacker.location = defender.location = room
        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(defender, NoOpAction(defender))
        engine.queue_action(attacker, KillAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), patch(
            "combat.damage_processor.delay"
        ), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        corpse = next(obj for obj in room.contents if obj not in (attacker, defender))
        self.assertIn(loot, corpse.contents)
        defender.drop_loot.assert_called_once_with(attacker)

    def test_combatant_removed_after_defeat(self):
        attacker = Dummy(key="attacker")
        defender = Dummy(key="defender")
        room = MagicMock()
        room.contents = [attacker, defender]
        attacker.location = defender.location = room
        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(defender, NoOpAction(defender))
        engine.queue_action(attacker, KillAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), patch(
            "combat.damage_processor.delay"
        ), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        participants = [p.actor for p in engine.participants]
        self.assertNotIn(defender, participants)


if __name__ == "__main__":
    unittest.main()
