import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import django
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest

from utils import prototype_manager


@override_settings(DEFAULT_HOME=None)
class TestLoadAllPrototypes(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(
            prototype_manager.CATEGORY_DIRS,
            {
                "room": Path(self.tmp.name) / "rooms",
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        prototype_manager.CATEGORY_DIRS["room"].mkdir(parents=True, exist_ok=True)

    def test_skip_non_numeric_files(self):
        numeric_file = prototype_manager.CATEGORY_DIRS["room"] / "100.json"
        with numeric_file.open("w") as f:
            json.dump({"vnum": 100}, f)

        non_numeric_file = prototype_manager.CATEGORY_DIRS["room"] / "MIDGARD.json"
        with non_numeric_file.open("w") as f:
            json.dump([{"vnum": 200}], f)

        result = prototype_manager.load_all_prototypes("room")
        assert 100 in result
        assert all(key != 200 for key in result)
