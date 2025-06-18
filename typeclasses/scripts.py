"""Custom script typeclasses used by the game."""

from random import randint, choice
from evennia.utils import logger, inherits_from
from django.conf import settings
from evennia.scripts.scripts import DefaultScript
from evennia.prototypes.prototypes import PROTOTYPE_TAG_CATEGORY
from evennia.prototypes.spawner import spawn


class Script(DefaultScript):
    """Base script typeclass.

    This lightweight subclass mirrors Evennia's ``DefaultScript`` but is
    defined for clarity and future customization.  Having a project-specific
    script parent makes it easy to tag or extend all in-game scripts later on.
    """

    pass





class RestockScript(Script):
    """
    A script for a shop room that periodically restocks its inventory.
    """

    def at_script_creation(self):
        self.interval = 3600

    def at_repeat(self):
        """
        The primary hook for timed scripts
        """
        if not (storage := self.obj.db.storage):
            # the object we're attached to has no storage location, so it can't hold stock
            return
        if not (inventory := self.obj.db.inventory):
            # we don't have an inventory list attribute set up
            return

        # go through the inventory listing and possibly restock a few of everything
        for prototype, max_count in inventory:
            # current stock of this type
            in_stock = [
                obj
                for obj in storage.contents
                if obj.tags.has(prototype, category=PROTOTYPE_TAG_CATEGORY)
            ]
            if len(in_stock) >= max_count:
                # already enough of these
                continue
            # get a random number of new stock, only process if >0
            if new_stock := randint(0, 3):
                # cap it so we don't exceed max
                new_stock = min(new_stock, max_count - len(in_stock))
                # make some new stuff!
                objs = spawn(*[prototype] * new_stock)
                # customize with the material options
                for obj in objs:
                    # make sure it has an initial value
                    obj.db.value = obj.db.value or 1
                    # add to the shop stock
                    self.obj.add_stock(obj)


class GlobalTick(Script):
    """A global ticker that regenerates health/mana/stamina and refreshes prompts."""

    def at_script_creation(self):
        self.interval = 60
        self.persistent = True

    def at_repeat(self):
        from evennia.utils.search import search_tag
        from .characters import PlayerCharacter
        from world.system import state_manager

        # Advance timers on all characters before applying regen
        state_manager.tick_all()

        tickables = search_tag(key="tickable")
        for obj in tickables:
            if not hasattr(obj, "traits"):
                continue

            state_manager.apply_regen(obj)

            if hasattr(obj, "refresh_prompt"):
                obj.refresh_prompt()


class DecayScript(Script):
    """Delete the attached object after a delay."""

    def at_script_creation(self):
        self.key = "decay"
        self.desc = "Delete the object after a delay"
        self.persistent = True
        # keep checking until we delete the object
        self.repeats = -1
        self.db.room_only = False

    def at_repeat(self):
        obj = self.obj
        if not obj:
            self.stop()
            return

        if self.db.room_only:
            location = obj.location
            if location:
                from typeclasses.rooms import Room

                if not inherits_from(location, Room):
                    return
            else:
                return

        location = obj.location
        if location and getattr(obj.db, "is_corpse", False):
            name = obj.db.corpse_of or obj.key
            location.msg_contents(
                f"|gThe corpse of {name} decomposes and crumbles to dust.|n"
            )

        obj.delete()
        self.stop()
