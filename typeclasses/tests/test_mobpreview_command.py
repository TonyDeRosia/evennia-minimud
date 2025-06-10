from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from world import prototypes


@override_settings(DEFAULT_HOME=None)
class TestMobPreviewCommand(EvenniaTest):
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

    def test_mobpreview_spawns_and_deletes(self):
        prototypes.register_npc_prototype("goblin", {"key": "goblin"})
        npc = MagicMock()
        with patch("evennia.prototypes.spawner.spawn", return_value=[npc]) as mock_spawn, \
             patch("evennia.utils.utils.delay", lambda t, func, *a, **kw: func(*a, **kw)):
            self.char1.execute_cmd("@mobpreview goblin")
        mock_spawn.assert_called()
        npc.move_to.assert_called_with(self.char1.location, quiet=True)
        npc.delete.assert_called()
