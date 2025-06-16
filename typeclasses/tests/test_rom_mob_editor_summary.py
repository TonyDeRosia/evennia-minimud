from evennia.utils.test_resources import EvenniaTest
from commands import rom_mob_editor

class TestRomMobEditorSummary(EvenniaTest):
    def test_summary_handles_list_skills(self):
        self.char1.ndb.mob_proto = {"skills": ["slash(100%)"]}
        self.char1.ndb.mob_vnum = 1
        out = rom_mob_editor._summary(self.char1)
        assert "slash(100%)" in out

