from unittest import mock
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from utils import prototype_manager, vnum_registry
from utils.mob_proto import register_prototype, load_npc_prototypes
from world.scripts.mob_db import get_mobdb


@override_settings(DEFAULT_HOME=None)
class TestMobProtoDisk(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = TemporaryDirectory()
        patcher1 = mock.patch.dict(
            prototype_manager.CATEGORY_DIRS,
            {"npc": Path(self.tmp.name)},
        )
        patcher2 = mock.patch.object(
            settings, "PROTOTYPE_NPC_FILE", Path(self.tmp.name) / "npcs.json"
        )
        patcher3 = mock.patch.object(
            settings, "VNUM_REGISTRY_FILE", Path(self.tmp.name) / "vnums.json"
        )
        patcher4 = mock.patch.object(
            vnum_registry, "_REG_PATH", Path(self.tmp.name) / "vnums.json"
        )
        for p in (patcher1, patcher2, patcher3, patcher4):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_register_writes_file(self):
        data = {"key": "orc"}
        vnum = register_prototype(data, vnum=1)
        path = prototype_manager.CATEGORY_DIRS["npc"] / f"{vnum}.json"
        assert path.exists()
        with path.open() as f:
            saved = json.load(f)
        assert saved["key"] == "orc"

    def test_loader_populates_mobdb(self):
        data = {"key": "ogre"}
        vnum = register_prototype(data, vnum=2)
        mob_db = get_mobdb()
        mob_db.db.vnums = {}
        load_npc_prototypes()
        assert mob_db.get_proto(vnum)["key"] == "ogre"
