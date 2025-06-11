import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.test_resources import EvenniaTest


class TestMenuUtils(EvenniaTest):
    def test_add_back_skip_from_dict(self):
        from utils.menu_utils import add_back_skip
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
        from utils.menu_utils import add_back_only
        def handler(caller, raw_string, **kwargs):
            return raw_string

        opts = add_back_only({"key": "_default", "goto": handler}, handler)
        self.assertEqual(len(opts), 2)
        self.assertEqual(opts[0]["key"], "_default")
        self.assertEqual(opts[1]["desc"], "Back")
        self.assertEqual(opts[1]["goto"](self.char1, ""), "back")

    def test_add_back_skip_from_list(self):
        from utils.menu_utils import add_back_skip
        def handler(caller, raw_string, **kwargs):
            return raw_string

        base = [{"desc": "Test", "goto": handler}]
        opts = add_back_skip(base, handler)
        self.assertEqual(len(opts), 3)
        self.assertEqual(opts[0]["desc"], "Test")
        self.assertEqual(opts[1]["goto"](self.char1, ""), "back")
        self.assertEqual(opts[2]["goto"](self.char1, ""), "skip")

    def test_toggle_multi_select(self):
        from utils.menu_utils import toggle_multi_select
        opts = ["a", "b", "c"]
        selected = []
        self.assertTrue(toggle_multi_select("1", opts, selected))
        self.assertIn("a", selected)
        self.assertTrue(toggle_multi_select("a", opts, selected))
        self.assertNotIn("a", selected)
        self.assertFalse(toggle_multi_select("d", opts, selected))

    def test_format_multi_select(self):
        from utils.menu_utils import format_multi_select
        opts = ["a", "b"]
        selected = ["b"]
        text = format_multi_select(opts, selected)
        self.assertIn("[ ] a", text)
        self.assertIn("[X] b", text)
