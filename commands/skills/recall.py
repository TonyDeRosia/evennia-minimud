from evennia.objects.models import ObjectDB
from ..command import Command
from world.system import state_manager


class CmdRecall(Command):
    """Teleport back to a safe location."""

    key = "recall"
    help_category = "General"

    def func(self):
        caller = self.caller
        if caller.traits.mana.current < 10:
            caller.msg("You do not have enough mana.")
            return
        if state_manager.is_on_cooldown(caller, "recall"):
            caller.msg("You cannot recall yet.")
            return
        location = caller.location
        if location and location.tags.has("no_recall", category="room_flag"):
            caller.msg("Mystical forces prevent recall from here.")
            return

        from typeclasses.rooms import Room

        objs = ObjectDB.objects.filter(
            db_attributes__db_key="room_id", db_attributes__db_value=200050
        )
        dest = None
        for obj in objs:
            if obj.is_typeclass(Room, exact=False):
                dest = obj
                break
        if not dest:
            caller.msg("The destination does not exist.")
            return

        caller.traits.mana.current -= 10
        state_manager.add_cooldown(caller, "recall", 15)
        if location:
            location.msg_contents(
                f"{caller.get_display_name(caller)} vanishes in a flash of light!",
                exclude=caller,
            )
        caller.msg("You focus on home and feel yourself pulled away...")
        caller.move_to(dest, quiet=True, move_type="teleport")
        caller.msg("You arrive at your destination.")
        dest.msg_contents(
            f"{caller.get_display_name(caller)} appears in a flash of light!",
            exclude=caller,
        )
