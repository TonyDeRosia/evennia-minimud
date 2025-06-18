from unittest import mock
from django.test import override_settings

from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest
from typeclasses.rooms import Room
from world.areas import find_area_by_vnum


@override_settings(DEFAULT_HOME=None)
class TestMidgardArea(EvenniaTest):
    def test_lookup_midgard(self):
        area = find_area_by_vnum(200050)
        assert area and area.key == "midgard"

    def test_create_and_teleport(self):
        from commands.building import CmdTeleport
        from world.scripts import create_midgard_area

        rooms_created, exits_created = create_midgard_area.create()
        assert rooms_created >= 1

        cmd = CmdTeleport()
        cmd.caller = self.char1
        cmd.caller.location = self.room1
        cmd.args = "200050"
        cmd.msg = mock.Mock()
        cmd.func()

        objs = ObjectDB.objects.filter(
            db_attributes__db_key="room_id", db_attributes__db_value=200050
        )
        target = None
        for obj in objs:
            if obj.is_typeclass(Room, exact=False):
                target = obj
                break
        assert target
        assert self.char1.location == target

        data = create_midgard_area.midgard_rooms[200050]
        assert target.key == data["name"]
        assert target.db.desc == data["desc"]
        assert target.db.exits.get("south")
        exit_objs = [ex for ex in target.exits if ex.key.lower() == "south"]
        assert exit_objs
        assert "s" in exit_objs[0].aliases.all()
