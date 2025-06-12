from unittest.mock import MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet


@override_settings(DEFAULT_HOME=None)
class TestMobTemplateCommand(EvenniaTest):
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

    def test_list_and_apply_template(self):
        self.char1.execute_cmd("@mobtemplate list")
        out = self.char1.msg.call_args[0][0]
        assert "Available templates" in out
        for name in ("warrior", "mystic", "wizard", "swashbuckler", "merchant"):
            assert name in out
        self.char1.msg.reset_mock()

        self.char1.execute_cmd("@mobtemplate wizard")
        data = self.char1.ndb.buildnpc
        assert data["mp"] >= 30
        assert "fireball" in data.get("spells", [])

    def test_template_with_shop(self):
        self.char1.execute_cmd("@mobtemplate merchant")
        data = self.char1.ndb.buildnpc
        assert data.get("shop")
        assert data.get("equipment")
