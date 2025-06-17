from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.rooms import Room


class TestRoomMinimap(EvenniaTest):
    def test_generate_map_marks_exits(self):
        room = self.room1
        room.db.coord = (0, 0)
        north = create.create_object(Room, key="north", location=None)
        south = create.create_object(Room, key="south", location=None)
        east = create.create_object(Room, key="east", location=None)
        west = create.create_object(Room, key="west", location=None)
        north.db.coord = (0, 1)
        south.db.coord = (0, -1)
        east.db.coord = (1, 0)
        west.db.coord = (-1, 0)
        room.db.exits = {"north": north, "south": south, "east": east, "west": west}

        map_out = room.generate_map(self.char1)
        self.assertIn("[X]", map_out)
        self.assertIn("[ ]", map_out)
        self.assertIn("-", map_out)
        self.assertIn("|", map_out)

    def test_map_in_return_appearance(self):
        room = self.room1
        room.db.coord = (0, 0)
        self.room2.db.coord = (0, 1)
        room.db.exits = {"north": self.room2}
        out = room.return_appearance(self.char1)
        self.assertIn("[X]", out.splitlines()[0])
