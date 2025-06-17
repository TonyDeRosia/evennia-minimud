from evennia.utils.test_resources import EvenniaTest
from commands import redit

class TestReditSummary(EvenniaTest):
    def test_summary_shows_area(self):
        self.char1.ndb.room_protos = {5: {"vnum": 5, "key": "Room", "area": "zone"}}
        self.char1.ndb.current_vnum = 5
        out = redit._summary(self.char1)
        assert "Area: zone" in out

    def test_summary_omits_missing_area(self):
        self.char1.ndb.room_protos = {5: {"vnum": 5, "key": "Room"}}
        self.char1.ndb.current_vnum = 5
        out = redit._summary(self.char1)
        assert "Area:" not in out
