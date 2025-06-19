import unittest
from unittest.mock import MagicMock, patch

from combat.engine import CombatEngine
from combat.combat_actions import (
    AttackAction,
    SkillAction,
    SpellAction,
    CombatResult,
    Action,
)
from combat.combat_skills import ShieldBash
from combat.damage_types import DamageType
from combat.ai_combat import npc_take_turn
from typeclasses.gear import BareHand


class Dummy:
    def __init__(self, hp=10):
        self.hp = hp
        self.key = "dummy"
        self.location = MagicMock()
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=0)
        self.traits.health = MagicMock(value=hp, max=hp)
        self.traits.mana = MagicMock(current=20)
        self.traits.stamina = MagicMock(current=20)
        self.cooldowns = MagicMock()
        self.cooldowns.ready.return_value = True
        self.tags = MagicMock()
        self.wielding = []
        self.db = type(
            "DB",
            (),
            {
                "temp_bonuses": {},
                "status_effects": {},
                "active_effects": {},
                "get": lambda *a, **k: 0,
            },
        )()
        self.attack = MagicMock()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.cast_spell = MagicMock()
        self.use_skill = MagicMock()

    def get_attack_weapon(self):
        if self.wielding:
            return self.wielding[0]
        if getattr(self.db, "natural_weapon", None):
            return self.db.natural_weapon
        from typeclasses.gear import BareHand
        return BareHand()


class KillAction(Action):
    def resolve(self):
        self.target.hp = 0
        return CombatResult(self.actor, self.target, "boom")


class TestAttackAction(unittest.TestCase):
    def test_attack_deals_damage(self):
        attacker = Dummy()
        defender = Dummy()
        weapon = MagicMock()
        weapon.damage = 5
        weapon.damage_type = DamageType.SLASHING
        weapon.at_attack = MagicMock()
        attacker.wielding = [weapon]
        attacker.location = defender.location

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), \
             patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        self.assertEqual(defender.hp, 5)
        weapon.at_attack.assert_not_called()

    def test_attack_damage_scaled_by_stats(self):
        attacker = Dummy()
        defender = Dummy()
        weapon = MagicMock()
        weapon.damage = 5
        weapon.damage_type = DamageType.SLASHING
        weapon.at_attack = MagicMock()
        attacker.wielding = [weapon]
        attacker.location = defender.location

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), \
             patch("random.randint", return_value=0), \
             patch("world.system.state_manager.get_effective_stat") as mock_get:
            def getter(obj, stat):
                if obj is attacker and stat == "STR":
                    return 10
                if obj is attacker and stat == "DEX":
                    return 5
                return 0

            mock_get.side_effect = getter
            engine.start_round()
            engine.process_round()

        self.assertEqual(defender.hp, 4)

    def test_attack_uses_damage_dice_when_damage_missing(self):
        attacker = Dummy()
        defender = Dummy()
        weapon = MagicMock()
        weapon.damage = None
        weapon.damage_type = DamageType.SLASHING
        weapon.db = type("db", (), {"damage_dice": "1d4", "dmg": 0})()
        weapon.at_attack = MagicMock()
        attacker.wielding = [weapon]
        attacker.location = defender.location

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), \
             patch("world.system.state_manager.get_effective_stat", return_value=0), \
             patch("combat.engine.combat_math.roll_dice_string", return_value=3) as mock_roll:
            engine.start_round()
            engine.process_round()

        self.assertEqual(defender.hp, 3)
        mock_roll.assert_called_with("1d4")

    def test_attack_uses_db_damage_mapping(self):
        attacker = Dummy()
        defender = Dummy()
        weapon = MagicMock()
        weapon.damage = None
        weapon.damage_type = None
        weapon.db = type("db", (), {"damage": {"slash": "1d4", "fire": "1d6"}})()
        weapon.at_attack = MagicMock()
        attacker.wielding = [weapon]
        attacker.location = defender.location

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), \
             patch("world.system.state_manager.get_effective_stat", return_value=0), \
             patch("random.randint", return_value=0), \
             patch("combat.combat_actions.roll_dice_string", side_effect=[2, 3]) as mock_roll:
            engine.start_round()
            engine.process_round()

        self.assertEqual(defender.hp, 5)
        mock_roll.assert_any_call("1d4")
        mock_roll.assert_any_call("1d6")

    def test_unarmed_attack_mentions_fists(self):
        attacker = Dummy()
        defender = Dummy()
        attacker.wielding = []
        attacker.location = defender.location

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), \
             patch("world.system.stat_manager.check_hit", return_value=False), \
             patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        calls = [c.args[0] for c in attacker.location.msg_contents.call_args_list]
        self.assertTrue(any("fists" in msg for msg in calls))

def test_npc_attack_uses_natural_weapon(self):
    attacker = Dummy()
    defender = Dummy()
    attacker.wielding = []
    attacker.location = defender.location
    attacker.db.natural_weapon = {
        "damage_dice": "1d1",
        "damage_bonus": 4,
        "damage_type": DamageType.PIERCING,
    }

    engine = CombatEngine([attacker, defender], round_time=0)
    engine.queue_action(attacker, AttackAction(attacker, defender))

    with patch("world.system.state_manager.apply_regen"), \
         patch("world.system.state_manager.get_effective_stat", return_value=0), \
         patch("random.randint", return_value=0):
        engine.start_round()
        engine.process_round()

    self.assertEqual(defender.hp, 5)


def test_barehand_attack_mentions_fists():
    attacker = Dummy()
    defender = Dummy()
    attacker.at_emote = MagicMock()
    with patch("world.system.stat_manager.check_hit", return_value=False):
        BareHand().at_attack(attacker, defender)

    attacker.at_emote.assert_called()
    msg = attacker.at_emote.call_args[0][0]
    assert "fists" in msg

class TestCombatVictory(unittest.TestCase):
    def test_handle_defeat_removes_participant(self):
        a = Dummy()
        b = Dummy()
        a.location = b.location
        engine = CombatEngine([a, b], round_time=0)
        engine.queue_action(a, KillAction(a, b))
        with patch("world.system.state_manager.apply_regen"):
            engine.start_round()
            engine.process_round()
        self.assertNotIn(b, [p.actor for p in engine.participants])


class TestNPCBehaviors(unittest.TestCase):
    def test_low_hp_triggers_callback(self):
        npc = Dummy()
        npc.traits.health.value = 2
        npc.traits.health.max = 10
        npc.on_low_hp = MagicMock()
        target = Dummy()
        npc_take_turn(None, npc, target)
        npc.on_low_hp.assert_called()




class TestSpellExample(unittest.TestCase):
    def test_spell_action_calls_cast(self):
        caster = Dummy()
        target = Dummy()
        caster.location = target.location
        caster.cast_spell = MagicMock()
        engine = CombatEngine([caster, target], round_time=0)
        engine.queue_action(caster, SpellAction(caster, "fireball", target))
        with patch("world.system.state_manager.apply_regen"), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()
        caster.cast_spell.assert_called_with("fireball", target)


def test_auto_attack_uses_combat_target():
    attacker = Dummy()
    defender = Dummy(hp=2)
    attacker.location = defender.location
    attacker.db.natural_weapon = {
        "damage_dice": "1d1",
        "damage_type": DamageType.BLUDGEONING,
    }
    attacker.db.combat_target = defender

    engine = CombatEngine([attacker, defender], round_time=0)

    with patch("world.system.state_manager.apply_regen"), \
         patch("world.system.state_manager.get_effective_stat", return_value=0), \
         patch("evennia.utils.delay"), \
         patch("random.randint", return_value=0):
        engine.start_round()
        engine.process_round()
        assert defender.hp == 1

        engine.process_round()
        assert defender.hp == 0


def test_haste_grants_extra_attacks():
    attacker = Dummy()
    defender = Dummy()
    attacker.location = defender.location
    attacker.db.natural_weapon = {
        "damage_dice": "1d1",
        "damage_type": DamageType.BLUDGEONING,
    }
    attacker.db.combat_target = defender

    engine = CombatEngine([attacker, defender], round_time=0)

    with patch("world.system.state_manager.apply_regen"), \
         patch("world.system.state_manager.get_effective_stat") as mock_get, \
         patch("evennia.utils.delay"), \
         patch("combat.combat_utils.roll_evade", return_value=False), \
         patch("world.system.stat_manager.randint", return_value=1):

        def getter(obj, stat):
            if obj is attacker and stat == "haste":
                return 55
            return 0

        mock_get.side_effect = getter

        engine.start_round()
        engine.process_round()

    assert defender.hp == 8


def test_npc_damage_dice_with_bonus():
    attacker = Dummy()
    defender = Dummy()
    attacker.location = defender.location
    attacker.db.damage_dice = "1d6"
    attacker.db.damage_bonus = 2
    attacker.damage_type = DamageType.BLUDGEONING

    engine = CombatEngine([attacker, defender], round_time=0)
    engine.queue_action(attacker, AttackAction(attacker, defender))

    with patch("world.system.state_manager.apply_regen"), \
         patch("world.system.state_manager.get_effective_stat", return_value=0), \
         patch("world.system.stat_manager.check_hit", return_value=True), \
         patch("world.system.stat_manager.roll_crit", return_value=False), \
         patch("combat.engine.combat_math.roll_evade", return_value=False), \
         patch("combat.engine.combat_math.roll_parry", return_value=False), \
         patch("combat.engine.combat_math.roll_block", return_value=False), \
         patch("combat.engine.combat_math.roll_dice_string", return_value=4) as mock_roll, \
         patch("evennia.utils.delay"):
        engine.start_round()
        engine.process_round()

    assert defender.hp == 4


def test_npc_damage_dice_fallback_to_2d6():
    attacker = Dummy()
    defender = Dummy()
    attacker.location = defender.location
    attacker.db.damage_bonus = 1
    attacker.damage_type = DamageType.BLUDGEONING

    engine = CombatEngine([attacker, defender], round_time=0)
    engine.queue_action(attacker, AttackAction(attacker, defender))

    with patch("world.system.state_manager.apply_regen"), \
         patch("world.system.state_manager.get_effective_stat", return_value=0), \
         patch("world.system.stat_manager.check_hit", return_value=True), \
         patch("world.system.stat_manager.roll_crit", return_value=False), \
         patch("combat.engine.combat_math.roll_evade", return_value=False), \
         patch("combat.engine.combat_math.roll_parry", return_value=False), \
         patch("combat.engine.combat_math.roll_block", return_value=False), \
         patch("combat.engine.combat_math.roll_dice_string", return_value=1) as mock_roll, \
         patch("evennia.utils.delay"):
        engine.start_round()
        engine.process_round()

    assert defender.hp == 8
    mock_roll.assert_called_with("2d6")


def test_round_output_blank_line():
    attacker = Dummy()
    defender = Dummy()
    attacker.location = defender.location
    attacker.db.combat_target = defender
    defender.db.combat_target = attacker

    engine = CombatEngine([attacker, defender], round_time=0)
    engine.queue_action(attacker, AttackAction(attacker, defender))

    with patch("world.system.state_manager.apply_regen"), \
         patch("random.randint", return_value=0):
        engine.start_round()
        engine.process_round()

    calls = [c.args[0] for c in attacker.location.msg_contents.call_args_list]
    assert calls[-1] == "\n"


def test_round_output_multiple_combatants_separated():
    a = Dummy()
    b = Dummy()
    c = Dummy()
    a.location = b.location = c.location
    a.db.combat_target = b
    b.db.combat_target = c
    c.db.combat_target = a

    engine = CombatEngine([a, b, c], round_time=0)
    engine.queue_action(a, AttackAction(a, b))

    with patch("world.system.state_manager.apply_regen"), patch("random.randint", return_value=0):
        engine.start_round()
        engine.process_round()

    calls = [c.args[0] for c in a.location.msg_contents.call_args_list]
    assert calls[1] == "\n"
    assert calls[3] == "\n"

