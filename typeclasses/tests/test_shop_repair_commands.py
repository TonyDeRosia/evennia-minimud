from unittest.mock import MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from world import prototypes


@override_settings(DEFAULT_HOME=None)
class TestShopRepairCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(
            settings,
            "PROTOTYPE_NPC_FILE",
            Path(self.tmp.name) / "npcs.json",
        )
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_shop_and_repair_setup(self):
        self.char1.execute_cmd("@mcreate merchant")
        self.char1.execute_cmd("@makeshop merchant")
        self.char1.execute_cmd("@shopset merchant buy 120")
        self.char1.execute_cmd("@makerepair merchant")
        self.char1.execute_cmd("@repairset merchant cost 200")
        reg = prototypes.get_npc_prototypes()
        shop = reg["merchant"]["shop"]
        repair = reg["merchant"]["repair"]
        assert shop["buy_percent"] == 120
        assert repair["cost_percent"] == 200
