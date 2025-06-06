from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings

from commands.guilds import GuildCmdSet
from world.guilds import find_guild


@override_settings(DEFAULT_HOME=None)
class TestGuildCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()
        self.char1.cmdset.add_default(GuildCmdSet)
        self.char2.cmdset.add_default(GuildCmdSet)
        # give char1 builder perms for management commands
        self.char1.permissions.add("Builder")

    def test_create_and_membership(self):
        # create a guild
        self.char1.execute_cmd("gcreate testguild")
        idx, guild = find_guild("testguild")
        self.assertNotEqual(idx, -1)
        # add char1 as initial member
        guild.members[str(self.char1.id)] = 0
        from world.guilds import update_guild
        update_guild(idx, guild)
        self.char1.db.guild = "testguild"
        self.char1.db.guild_points = {"testguild": 0}
        self.char1.db.guild_rank = ""

        # char2 requests to join
        self.char2.execute_cmd("gjoin testguild")
        self.assertEqual(self.char2.db.guild_request, "testguild")

        # char1 accepts
        self.char1.execute_cmd(f"gaccept {self.char2.key}")
        self.assertEqual(self.char2.db.guild, "testguild")
        self.assertIsNone(self.char2.db.guild_request)

        # promote and then kick
        self.char1.execute_cmd(f"gpromote {self.char2.key} 5")
        self.assertEqual(self.char2.db.guild_points.get("testguild"), 5)
        self.char1.execute_cmd(f"gkick {self.char2.key}")
        self.assertEqual(self.char2.db.guild, "")

    def test_npc_roles(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        npc_master = create.create_object(NPC, key="Master", location=self.room1)
        npc_master.cmdset.add_default(GuildCmdSet)
        npc_master.msg = MagicMock()
        npc_master.tags.add("guildmaster", category="npc_role")

        npc_master.execute_cmd("gcreate roleguild")
        idx, guild = find_guild("roleguild")
        self.assertNotEqual(idx, -1)

        guild.members[str(self.char1.id)] = 0
        guild.members[str(self.char2.id)] = 0
        from world.guilds import update_guild
        update_guild(idx, guild)

        npc_master.db.guild = "roleguild"
        self.char1.db.guild = "roleguild"
        self.char2.db.guild = "roleguild"
        npc_master.execute_cmd(f"gkick {self.char1.key}")
        self.assertEqual(self.char1.db.guild, "")

        npc_rec = create.create_object(NPC, key="Rec", location=self.room1)
        npc_rec.cmdset.add_default(GuildCmdSet)
        npc_rec.msg = MagicMock()
        npc_rec.tags.add("guild_receptionist", category="npc_role")
        npc_rec.db.guild = "roleguild"
        self.char2.db.guild_points = {"roleguild": 0}
        self.char2.db.guild_rank = ""

        npc_rec.execute_cmd(f"gpromote {self.char2.key}")
        self.assertEqual(self.char2.db.guild_points.get("roleguild"), 1)
        npc_rec.execute_cmd("gcreate shouldfail")
        idx2, _ = find_guild("shouldfail")
        self.assertEqual(idx2, -1)
