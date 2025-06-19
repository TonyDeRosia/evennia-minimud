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
        room.db.coord = (0, 0)
        
        # Create neighboring rooms with coordinates
        north = create.create_object(Room, key="north", location=None)
        south = create.create_object(Room, key="south", location=None)
        east = create.create_object(Room, key="east", location=None)
        west = create.create_object(Room, key="west", location=None)
        
        north.db.coord = (0, 1)
        south.db.coord = (0, -1)
        east.db.coord = (1, 0)
        west.db.coord = (-1, 0)
        
        # Assign exits to the central room
        room.db.exits = {
            "north": north,
            "south": south,
            "east": east,
            "west": west
        }
        
        map_output = room.generate_map(self.char1)
        expected = [
            "   [ ]   ",
            "[ ][X][ ]",
            "   [ ]   ",
        ]
        self.assertEqual(map_output.splitlines(), expected)

    def test_generate_map_defaults_to_zero_zero(self):
        room = self.room1
        room.db.coord = None
        
        map_output = room.generate_map(self.char1)
        expected = [
            "         ",
            "   [X]   ",
            "         ",
        ]
        self.assertEqual(map_output.splitlines(), expected)

    def test_map_in_return_appearance(self):
        room = self.room1
        room.db.coord = (0, 0)
        
        # Assign a northern room for minimal connection
        self.room2.db.coord = (0, 1)
        room.db.exits = {"north": self.room2}
        
        appearance = room.return_appearance(self.char1)
        map_lines = room.generate_map(self.char1).splitlines()

        # Confirm the blank line and map at the top of room description
        appearance_lines = appearance.splitlines()
        self.assertEqual(appearance_lines[0], "")
        self.assertEqual(appearance_lines[1:1 + len(map_lines)], map_lines)
        self.assertEqual(appearance_lines[1 + len(map_lines)], "")

    def test_xygrid_map_and_appearance(self):
        # Center + 4 directions
        center = create.create_object(Room, key="center", location=None, nohome=True)
        north = create.create_object(Room, key="north", location=None, nohome=True)
        south = create.create_object(Room, key="south", location=None, nohome=True)
        east = create.create_object(Room, key="east", location=None, nohome=True)
        west = create.create_object(Room, key="west", location=None, nohome=True)
        
        # Assign coordinates
        center.db.coord = (1, 1)
        north.db.coord = (1, 2)
        south.db.coord = (1, 0)
        east.db.coord = (2, 1)
        west.db.coord = (0, 1)
        
        # Assign reciprocal exits
        center.db.exits = {"north": north, "south": south, "east": east, "west": west}
        north.db.exits = {"south": center}
        south.db.exits = {"north": center}
        east.db.exits = {"west": center}
        west.db.exits = {"east": center}
        
        # Expected 3x3 map with surrounding rooms
        expected_map = "\n".join([
            "   [ ]   ",
            "[ ][X][ ]",
            "   [ ]   ",
        ])
        
        generated_map = center.generate_map(self.char1)
        self.assertEqual(generated_map, expected_map)

        appearance = center.return_appearance(self.char1)
        appearance_lines = appearance.splitlines()
        expected_lines = expected_map.splitlines()

        self.assertEqual(appearance_lines[0], "")
        self.assertEqual(
            appearance_lines[1:1 + len(expected_lines)], expected_lines
        )
        self.assertEqual(appearance_lines[1 + len(expected_lines)], "")
