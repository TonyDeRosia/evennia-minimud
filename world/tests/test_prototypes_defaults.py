import json
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from world import prototypes


class TestPrototypeDefaults(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(
            settings, "PROTOTYPE_NPC_FILE", Path(self.tmp.name) / "npcs.json"
        )
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_register_inserts_defaults(self):
        prototypes.register_npc_prototype("orc", {"key": "orc"})
        reg = prototypes.get_npc_prototypes()
        proto = reg["orc"]
        self.assertEqual(proto["npc_type"], "base")
        self.assertEqual(proto["race"], "human")
        self.assertEqual(proto["level"], 1)
        self.assertEqual(proto["damage"], 1)

    def test_load_inserts_defaults(self):
        path = Path(settings.PROTOTYPE_NPC_FILE)
        data = {"goblin": {"key": "goblin"}}
        with path.open("w") as f:
            json.dump(data, f)
        reg = prototypes.get_npc_prototypes()
        proto = reg["goblin"]
        self.assertEqual(proto["npc_type"], "base")
        self.assertEqual(proto["race"], "human")
        self.assertEqual(proto["level"], 1)
        self.assertEqual(proto["damage"], 1)
