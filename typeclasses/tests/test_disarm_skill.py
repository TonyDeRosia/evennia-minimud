from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from combat.engine import CombatEngine
from combat.combat_actions import SkillAction
from world.skills.disarm import Disarm
from world.system import stat_manager


@override_settings(DEFAULT_HOME=None)
class TestDisarmSkill(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.msg_contents = MagicMock()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()

        self.char2.attributes.add("_wielded", {"right": None, "left": None})
        self.weapon = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="sword", location=self.char2
        )
        self.weapon.tags.add("equipment", category="flag")
        self.weapon.tags.add("identified", category="flag")
        self.char2.at_wield(self.weapon)

    def _run_skill(self, hit=True, evade=False, parry=False):
        engine = CombatEngine([self.char1, self.char2], round_time=0)
        engine.queue_action(self.char1, SkillAction(self.char1, Disarm(), self.char2))
        with patch("world.system.state_manager.apply_regen"), \
             patch.object(stat_manager, "check_hit", return_value=hit), \
             patch("combat.combat_utils.roll_evade", return_value=evade), \
             patch("combat.combat_utils.roll_parry", return_value=parry), \
             patch("world.skills.skill.random", return_value=0), \
             patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

    def test_disarm_success(self):
        self._run_skill()
        self.assertNotIn(self.weapon, self.char2.wielding)
        calls = [c.args[0] for c in self.room1.msg_contents.call_args_list]
        self.assertTrue(any("disarm" in msg.lower() for msg in calls))

    def test_disarm_failure(self):
        self._run_skill(hit=False)
        self.assertIn(self.weapon, self.char2.wielding)
        calls = [c.args[0] for c in self.room1.msg_contents.call_args_list]
        self.assertTrue(any("fails" in msg or "misses" in msg for msg in calls))
