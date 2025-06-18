from unittest.mock import patch
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from combat.combat_skills import SKILL_CLASSES
from world.spells import SPELLS, Spell

class TestSkillAndSpellUsage(EvenniaTest):
    def setUp(self):
        super().setUp()
        # ensure characters have sample spell known
        self.char1.db.spells = [SPELLS["fireball"]]

    def test_cast_spell_applies_cost_and_cooldown(self):
        mana_before = self.char1.traits.mana.current
        result = self.char1.cast_spell("fireball", target=self.char2)
        self.assertIn("casts fireball", result.message)
        self.assertEqual(self.char1.traits.mana.current, mana_before - SPELLS["fireball"].mana_cost)
        self.assertTrue(self.char1.cooldowns.time_left("fireball", use_int=True))

    def test_use_skill_applies_cost_and_cooldown(self):
        skill_cls = SKILL_CLASSES["cleave"]
        stamina_before = self.char1.traits.stamina.current
        result = self.char1.use_skill("cleave", target=self.char2)
        self.assertEqual(self.char1.traits.stamina.current, stamina_before - skill_cls().stamina_cost)
        self.assertTrue(self.char1.cooldowns.time_left("cleave", use_int=True))


    def test_shield_bash_adds_status_effect(self):
        self.char2.hp = 10
        with patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_damage", return_value=4), \
              patch("world.system.state_manager.add_status_effect") as mock_add:
            self.char1.use_skill("shield bash", target=self.char2)
            mock_add.assert_called_with(self.char2, "stunned", 1)
            self.assertEqual(self.char2.hp, 6)

    def test_skill_evade_prevents_damage(self):
        self.char2.hp = 10
        with patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_evade", return_value=True), \
              patch("combat.combat_skills.roll_damage", return_value=4):
            result = self.char1.use_skill("cleave", target=self.char2)
        self.assertEqual(self.char2.hp, 10)
        self.assertIn("misses", result.message)
        self.assertIn("|C", result.message)

    def test_cast_spell_converts_dict(self):
        self.char1.db.spells = {"fireball": 100}
        result = self.char1.cast_spell("fireball", target=self.char2)
        self.assertIn("casts fireball", result.message)
        spells = self.char1.db.spells
        self.assertIsInstance(spells, list)
        self.assertIsInstance(spells[0], Spell)
        self.assertEqual(spells[0].key, "fireball")

    def test_skill_hit_and_miss_calculation(self):
        """Players should hit or miss based on stat calculations."""

        self.char2.hp = 10
        # First ensure a hit
        with patch("world.system.stat_manager.get_effective_stat") as get_stat, \
             patch("random.randint", return_value=20), \
             patch("combat.combat_skills.roll_damage", return_value=4):

            def getter(obj, stat):
                if obj is self.char1 and stat == "hit_chance":
                    return 90
                if obj is self.char2 and stat == "dodge":
                    return 10
                return 0

            get_stat.side_effect = getter
            result = self.char1.use_skill("cleave", target=self.char2)

        self.assertEqual(self.char2.hp, 6)
        self.assertIn("cleaves", result.message)

        # Now force a miss
        self.char2.hp = 10
        with patch("world.system.stat_manager.get_effective_stat") as get_stat, \
             patch("random.randint", return_value=100), \
             patch("combat.combat_skills.roll_damage", return_value=4):

            def getter(obj, stat):
                if obj is self.char1 and stat == "hit_chance":
                    return 10
                if obj is self.char2 and stat == "dodge":
                    return 30
                return 0

            get_stat.side_effect = getter
            result = self.char1.use_skill("cleave", target=self.char2)

        self.assertEqual(self.char2.hp, 10)
        self.assertIn("misses", result.message)

    def test_mob_hit_and_miss_calculation(self):
        """NPCs should use the same hit formula as players."""

        from evennia.utils import create
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="mob", location=self.room1)
        npc.db.skills = ["cleave"]

        self.char1.hp = 10
        with patch("world.system.stat_manager.get_effective_stat") as get_stat, \
             patch("random.randint", return_value=20), \
             patch("combat.combat_skills.roll_damage", return_value=4):

            def getter(obj, stat):
                if obj is npc and stat == "hit_chance":
                    return 90
                if obj is self.char1 and stat == "dodge":
                    return 10
                return 0

            get_stat.side_effect = getter
            result = npc.use_skill("cleave", target=self.char1)

        self.assertEqual(self.char1.hp, 6)
        self.assertIn("cleaves", result.message)

        self.char1.hp = 10
        with patch("world.system.stat_manager.get_effective_stat") as get_stat, \
             patch("random.randint", return_value=100), \
             patch("combat.combat_skills.roll_damage", return_value=4):

            def getter(obj, stat):
                if obj is npc and stat == "hit_chance":
                    return 10
                if obj is self.char1 and stat == "dodge":
                    return 30
                return 0

            get_stat.side_effect = getter
            result = npc.use_skill("cleave", target=self.char1)

        self.assertEqual(self.char1.hp, 10)
        self.assertIn("misses", result.message)

    def test_spell_and_skill_messages_use_colorized_names(self):
        """Casting and skill use should include color codes in messages."""

        self.char1.name_color = "g"
        self.char2.name_color = "r"

        with patch.object(self.room1, "msg_contents") as mock_msg:
            self.char1.cast_spell("fireball", target=self.char2)
            msg = mock_msg.call_args[0][0]
            self.assertIn("|g", msg)
            self.assertIn("|r", msg)

        with patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_evade", return_value=False), \
             patch("combat.combat_skills.roll_damage", return_value=4):
            result = self.char1.use_skill("cleave", target=self.char2)

        self.assertIn("|g", result.message)
        self.assertIn("|r", result.message)

