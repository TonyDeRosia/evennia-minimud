from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from combat.combat_actions import AttackAction
from typeclasses.npcs import BaseNPC
from world.system import state_manager


class TestAttackCooldowns(EvenniaTest):
    def test_player_attack_respects_cooldown(self):
        attacker = self.char1
        defender = self.char2
        attacker.location = self.room1
        defender.location = self.room1
        attacker.cooldowns.add("attack", 5)

        action = AttackAction(attacker, defender)
        valid, err = action.validate()
        assert not valid
        assert "recovering" in err.lower()

    def test_npc_attack_respects_cooldown(self):
        npc = create.create_object(BaseNPC, key="mob", location=self.room1)
        target = self.char1
        npc.cooldowns.add("attack", 5)

        action = AttackAction(npc, target)
        valid, err = action.validate()
        assert not valid
        assert "recovering" in err.lower()

