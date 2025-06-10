from evennia.utils.test_resources import EvenniaTest
from utils.menu_utils import add_back_skip, add_back_only


class TestMenuUtils(EvenniaTest):
    def test_add_back_skip_from_dict(self):
        def handler(caller, raw_string, **kwargs):
            return raw_string

        opts = add_back_skip({"key": "_default", "goto": handler}, handler)
        self.assertEqual(len(opts), 3)
        self.assertEqual(opts[0]["key"], "_default")
        self.assertEqual(opts[1]["desc"], "Back")
        self.assertEqual(opts[2]["desc"], "Skip")
        self.assertEqual(opts[1]["goto"](self.char1, ""), "back")
        self.assertEqual(opts[2]["goto"](self.char1, ""), "skip")

    def test_add_back_only(self):
        def handler(caller, raw_string, **kwargs):
            return raw_string

        opts = add_back_only({"key": "_default", "goto": handler}, handler)
        self.assertEqual(len(opts), 2)
        self.assertEqual(opts[0]["key"], "_default")
        self.assertEqual(opts[1]["desc"], "Back")
        self.assertEqual(opts[1]["goto"](self.char1, ""), "back")

    def test_add_back_skip_from_list(self):
        def handler(caller, raw_string, **kwargs):
            return raw_string

        base = [{"desc": "Test", "goto": handler}]
        opts = add_back_skip(base, handler)
        self.assertEqual(len(opts), 3)
        self.assertEqual(opts[0]["desc"], "Test")
        self.assertEqual(opts[1]["goto"](self.char1, ""), "back")
        self.assertEqual(opts[2]["goto"](self.char1, ""), "skip")
