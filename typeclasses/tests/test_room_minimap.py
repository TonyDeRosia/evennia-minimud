from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.rooms import Room


class TestRoomMinimap(EvenniaTest):
    def setUp(self):
        from django.conf import settings

        settings.TEST_ENVIRONMENT = True
        super().setUp()

    def test_generate_map_marks_exits(self):
        room = self.room1
        north = create.create_object(Room, key="north", location=None, nohome=True)
        south = create.create_object(Room, key="south", location=None, nohome=True)
        east = create.create_object(Room, key="east", location=None, nohome=True)
        west = create.create_object(Room, key="west", location=None, nohome=True)
        room.db.exits = {"north": north, "south": south, "east": east, "west": west}

        map_out = room.generate_map(self.char1)
        self.assertIn("^", map_out)
        self.assertIn("v", map_out)
        self.assertIn("<", map_out)
        self.assertIn(">", map_out)
        self.assertIn("[X]", map_out)

    def test_map_in_return_appearance(self):
        room = self.room1
        room.db.exits = {"north": self.room2}
        out = room.return_appearance(self.char1)
        map_lines = room.generate_map(self.char1).splitlines()
        self.assertEqual(out.splitlines()[:3], map_lines)

    def test_xygrid_map_and_appearance(self):
        center = create.create_object(Room, key="center", location=None, nohome=True)
        north = create.create_object(Room, key="north", location=None, nohome=True)
        south = create.create_object(Room, key="south", location=None, nohome=True)
        east = create.create_object(Room, key="east", location=None, nohome=True)
        west = create.create_object(Room, key="west", location=None, nohome=True)

        center.db.coords = (1, 1)
        north.db.coords = (1, 2)
        south.db.coords = (1, 0)
        east.db.coords = (2, 1)
        west.db.coords = (0, 1)

        center.db.exits = {"north": north, "south": south, "east": east, "west": west}
        north.db.exits = {"south": center}
        south.db.exits = {"north": center}
        east.db.exits = {"west": center}
        west.db.exits = {"east": center}

        expected_map = "\n".join([
            "  ^  ",
            "< [X] >",
            "  v  ",
        ])
        self.assertEqual(center.generate_map(self.char1), expected_map)

        appearance = center.return_appearance(self.char1)
        self.assertTrue(appearance.startswith(expected_map))
