"""
Object

The Object is the "naked" base class for things in the game world.

Note that the default Character, Room and Exit does not inherit from
this Object, but from their respective default implementations in the
evennia library. If you want to use this class as a parent to change
the other types, you can do so by adding this as a multiple
inheritance.

"""

from random import randint
from collections.abc import Mapping

from evennia.prototypes import spawner, prototypes
from evennia.objects.objects import DefaultObject
from evennia.contrib.game_systems.clothing import ContribClothing
from evennia.contrib.game_systems.clothing.clothing import get_worn_clothes
from evennia.utils import lazy_property
from world.triggers import TriggerManager
from utils.mob_utils import mobprogs_to_triggers

from utils.currency import COIN_VALUES

from commands.interact import GatherCmdSet
from world.system import stat_manager
from utils import normalize_slot


class ObjectParent:
    """
    This is a mixin that can be used to override *all* entities inheriting at
    some distance from DefaultObject (Objects, Exits, Characters and Rooms).

    Just add any method that exists on `DefaultObject` to this class. If one
    of the derived classes has itself defined that same hook already, that will
    take precedence.

    """

    def get_display_name(self, looker, **kwargs):
        """Return the short description or key for display."""
        return self.db.shortdesc or self.key


class Object(ObjectParent, DefaultObject):
    """
    This is the root typeclass object, implementing an in-game Evennia
    game object, such as having a location, being able to be
    manipulated or looked at, etc. If you create a new typeclass, it
    must always inherit from this object (or any of the other objects
    in this file, since they all actually inherit from BaseObject, as
    seen in src.object.objects).

    The BaseObject class implements several hooks tying into the game
    engine. By re-implementing these hooks you can control the
    system. You should never need to re-implement special Python
    methods, such as __init__ and especially never __getattribute__ and
    __setattr__ since these are used heavily by the typeclass system
    of Evennia and messing with them might well break things for you.


    * Base properties defined/available on all Objects

     key (string) - name of object
     name (string)- same as key
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation

     account (Account) - controlling account (if any, only set together with
                       sessid below)
     sessid (int, read-only) - session id (if any, only set together with
                       account above). Use `sessions` handler to get the
                       Sessions directly.
     location (Object) - current location. Is None if this is a room
     home (Object) - safety start-location
     has_account (bool, read-only)- will only return *connected* accounts
     contents (list of Objects, read-only) - returns all objects inside this
                       object (including exits)
     exits (list of Objects, read-only) - returns all exits from this
                       object, if any
     destination (Object) - only set if this object is an exit.
     is_superuser (bool, read-only) - True/False if this user is a superuser

    * Handlers available

     aliases - alias-handler: use aliases.add/remove/get() to use.
     permissions - permission-handler: use permissions.add/remove() to
                   add/remove new perms.
     locks - lock-handler: use locks.add() to add new lock strings
     scripts - script-handler. Add new scripts to object with scripts.add()
     cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     nicks - nick-handler. New nicks with nicks.add().
     sessions - sessions-handler. Get Sessions connected to this
                object with sessions.get()
     attributes - attribute-handler. Use attributes.add/remove/get.
     db - attribute-handler: Shortcut for attribute-handler. Store/retrieve
            database attributes using self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not create
            a database entry when storing data

    * Helper methods (see src.objects.objects.py for full headers)

     search(ostring, global_search=False, attribute_name=None,
             use_nicks=False, location=None, ignore_errors=False, account=False)
     execute_cmd(raw_string)
     msg(text=None, **kwargs)
     msg_contents(message, exclude=None, from_obj=None, **kwargs)
     move_to(destination, quiet=False, emit_to_obj=None, use_destination=True)
     copy(new_key=None)
     delete()
     is_typeclass(typeclass, exact=False)
     swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     access(accessing_obj, access_type='read', default=False)
     check_permstring(permstring)

    * Hooks (these are class methods, so args should start with self):

     basetype_setup()     - only called once, used for behind-the-scenes
                            setup. Normally not modified.
     basetype_posthook_setup() - customization in basetype, after the object
                            has been created; Normally not modified.

     at_object_creation() - only called once, when object is first created.
                            Object customizations go here.
     at_object_delete() - called just before deleting an object. If returning
                            False, deletion is aborted. Note that all objects
                            inside a deleted object are automatically moved
                            to their <home>, they don't need to be removed here.

     at_init()            - called whenever typeclass is cached from memory,
                            at least once every server restart/reload
     at_cmdset_get(**kwargs) - this is called just before the command handler
                            requests a cmdset from this object. The kwargs are
                            not normally used unless the cmdset is created
                            dynamically (see e.g. Exits).
     at_pre_puppet(account)- (account-controlled objects only) called just
                            before puppeting
     at_post_puppet()     - (account-controlled objects only) called just
                            after completing connection account<->object
     at_pre_unpuppet()    - (account-controlled objects only) called just
                            before un-puppeting
     at_post_unpuppet(account) - (account-controlled objects only) called just
                            after disconnecting account<->object link
     at_server_reload()   - called before server is reloaded
     at_server_shutdown() - called just before server is fully shut down

     at_access(result, accessing_obj, access_type) - called with the result
                            of a lock access check on this object. Return value
                            does not affect check result.

     at_pre_move(destination)             - called just before moving object
                        to the destination. If returns False, move is cancelled.
     announce_move_from(destination)         - called in old location, just
                        before move, if obj.move_to() has quiet=False
     announce_move_to(source_location)       - called in new location, just
                        after move, if obj.move_to() has quiet=False
     at_post_move(source_location)          - always called after a move has
                        been successfully performed.
     at_object_leave(obj, target_location)   - called when an object leaves
                        this object in any fashion
     at_object_receive(obj, source_location) - called when this object receives
                        another object

     at_traverse(traversing_object, source_loc) - (exit-objects only)
                              handles all moving across the exit, including
                              calling the other exit hooks. Use super() to retain
                              the default functionality.
     at_post_traverse(traversing_object, source_location) - (exit-objects only)
                              called just after a traversal has happened.
     at_failed_traverse(traversing_object)      - (exit-objects only) called if
                       traversal fails and property err_traverse is not defined.

     at_msg_receive(self, msg, from_obj=None, **kwargs) - called when a message
                             (via self.msg()) is sent to this obj.
                             If returns false, aborts send.
     at_msg_send(self, msg, to_obj=None, **kwargs) - called when this objects
                             sends a message to someone via self.msg().

     return_appearance(looker) - describes this object. Used by "look"
                                 command by default
     at_desc(looker=None)      - called by 'look' whenever the
                                 appearance is requested.
     at_get(getter)            - called after object has been picked up.
                                 Does not stop pickup.
     at_drop(dropper)          - called when this object has been dropped.
    at_say(speaker, message)  - by default, called if an object inside this
                                 object speaks

    """

    def at_object_creation(self):
        """Set default attributes when object is first created."""
        super().at_object_creation()
        if getattr(self.db, "weight", None) is None:
            self.db.weight = 0
        if getattr(self.db, "display_priority", None) is None:
            self.db.display_priority = "item"
        if self.db.obj_triggers is None:
            self.db.obj_triggers = {}

        if self.db.obj_programs and not self.db.obj_triggers:
            self.db.obj_triggers = mobprogs_to_triggers(self.db.obj_programs)

        if self.db.obj_triggers:
            self.trigger_manager.start_random_triggers()

    @lazy_property
    def trigger_manager(self):
        """Access :class:`~world.triggers.TriggerManager`."""
        return TriggerManager(self, attr="obj_triggers")

    def check_triggers(self, event, **kwargs):
        self.trigger_manager.check(event, **kwargs)

    def return_appearance(self, looker, **kwargs):
        text = super().return_appearance(looker, **kwargs)
        if looker != self:
            self.check_triggers("on_look", looker=looker)
        return text

    def at_use(self, user, **kwargs):
        """Generic hook for using an object."""
        self.check_triggers("on_use", user=user)

    def at_drop(self, dropper, **kwargs):
        """
        Make sure that wielded weapons are unwielded.
        """
        if self in dropper.wielding:
            dropper.at_unwield(self)
        super().at_drop(dropper, **kwargs)
        from world.system import stat_manager

        stat_manager.recalculate_stats(dropper)

    def at_pre_move(self, destination, move_type="move", **kwargs):
        """Prevent moving if the stationary flag is set."""
        if self.tags.has("stationary", category="flag"):
            mover = kwargs.get("caller") or kwargs.get("mover")
            if mover:
                mover.msg(f"{self.get_display_name(mover)} refuses to budge.")
            return False
        return super().at_pre_move(destination, move_type=move_type, **kwargs)

    def at_object_delete(self):
        """Clean up bonuses if this item is equipped when deleted."""
        if wearer := self.db.worn_by:
            if isinstance(wearer.db.equipment, Mapping):
                for slot, itm in list(wearer.db.equipment.items()):
                    if itm == self:
                        wearer.db.equipment.pop(slot, None)
                        break
            stat_manager.remove_bonuses(wearer, self)
        return True


class ClothingObject(ObjectParent, ContribClothing):

    def at_object_creation(self):
        """Ensure clothing items start identified unless specified."""
        super().at_object_creation()
        if getattr(self.db, "identified", None) is None:
            self.db.identified = True

    def wear(self, wearer, wearstyle, quiet=False):
        """Only wearable if flagged as equipment and identified."""
        if not self.tags.has("equipment", category="flag"):
            wearer.msg(f"{self.get_display_name(wearer)} can't be worn.")
            return
        if not self.tags.has("identified", category="flag"):
            wearer.msg(f"You don't know how to use {self.get_display_name(wearer)}.")
            return
        # honor slot tags by normalizing to canonical names
        if slots := self.tags.get(category="slot", return_list=True):
            for slot in slots:
                canonical = normalize_slot(slot)
                if canonical and not self.tags.has(canonical, category="slot"):
                    self.tags.add(canonical, category="slot")

        # replace any existing item in the same slot
        if not isinstance(wearer.db.equipment, Mapping):
            wearer.db.equipment = {}
        slot = self.db.slot or self.db.clothing_type
        if slot:
            slot = normalize_slot(slot) or slot
            if (existing := wearer.db.equipment.get(slot)):
                existing.remove(wearer, quiet=quiet)

        # shields can't be worn with two-handed weapons
        if self.tags.has("shield", category="flag"):
            for weap in wearer.wielding:
                is_twohanded = getattr(weap, "is_twohanded", lambda: False)()
                if is_twohanded:
                    wearer.msg(
                        "You cannot use a shield while wielding a two-handed weapon."
                    )
                    return

        result = super().wear(wearer, wearstyle, quiet=quiet)
        self.location = None
        wearer.update_carry_weight()
        self.db.worn_by = wearer
        # store equipped item in the character's equipment mapping
        slot = self.db.slot or self.db.clothing_type
        if not slot:
            if slots := self.tags.get(category="slot", return_list=True):
                slot = slots[0]
        if slot:
            slot = normalize_slot(slot) or slot
            wearer.db.equipment[slot] = self
        stat_manager.apply_item_bonuses_once(wearer, self)
        self.db.worn = True
        return result

    def remove(self, wearer, quiet=False):
        """Return to inventory when removed."""
        result = super().remove(wearer, quiet=quiet)
        self.location = wearer
        wearer.update_carry_weight()
        self.db.worn_by = None
        slot = self.db.slot or self.db.clothing_type
        if not slot:
            if slots := self.tags.get(category="slot", return_list=True):
                slot = slots[0]
        if isinstance(wearer.db.equipment, Mapping) and slot:
            slot = normalize_slot(slot) or slot
            wearer.db.equipment.pop(slot, None)
        stat_manager.remove_item_bonuses(wearer, self)
        self.db.worn = False
        return result


class GatherNode(Object):
    """
    An object which, when interacted with, allows a player to gather a material resource.
    """

    def at_object_creation(self):
        """
        Do some initial set-up
        """
        super().at_object_creation()
        self.locks.add("get:false()")
        self.cmdset.add_default(GatherCmdSet)

    def get_display_footer(self, looker, **kwargs):
        return "You can |wgather|n from this."

    def at_gather(self, chara, **kwargs):
        """
        Creates the actual material object for the player to collect.
        """
        if not (proto_key := self.db.spawn_proto):
            # somehow this node has no material to spawn
            chara.msg(
                f"The {self.get_display_name(chara)} disappears in a puff of confusion."
            )
            # get rid of ourself, since we're broken
            self.delete()
            return

        if not (remaining := self.db.gathers):
            # this node has been used up
            chara.msg(f"There is none left.")
            # get rid of ourself, since we're empty
            self.delete()
            return

        # grab a randomized amount to spawn
        amt = randint(1, min(remaining, 3))

        # spawn the items!
        objs = spawner.spawn(*[proto_key] * amt)
        for obj in objs:
            # move to the gathering character
            obj.location = chara

        if amt == remaining:
            chara.msg(f"You collect the last {obj.get_numbered_name(amt, chara)[1]}.")
            self.delete()
        else:
            chara.msg(f"You collect {obj.get_numbered_name(amt, chara)[1]}.")
            self.db.gathers -= amt


class CoinPile(Object):
    """A small pile of coins dropped in the world."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.coin_type = "copper"
        self.db.amount = 0
        self.db.weight = 0
        self.db.from_pouch = False

    def get_display_name(self, looker, **kwargs):
        ctype = (self.db.coin_type or "coin").capitalize()
        amount = int(self.db.amount or 0)
        return f"{amount} {ctype} coin{'s' if amount != 1 else ''}"

    def at_after_move(self, source_location, move_type="move", **kwargs):
        super().at_after_move(source_location, move_type=move_type, **kwargs)
        dest = self.location
        if not dest:
            return
        if dest.is_typeclass("typeclasses.characters.Character", exact=False) and self.db.from_pouch:
            wallet = dest.db.coins or {}
            ctype = self.db.coin_type
            wallet[ctype] = int(wallet.get(ctype, 0)) + int(self.db.amount or 0)
            dest.db.coins = wallet
            dest.msg(
                f"You receive {self.db.amount} {ctype} coin{'s' if int(self.db.amount or 0) != 1 else ''}."
            )
            self.db.from_pouch = False
            # when picked up via `get`, Evennia will call `at_get` after this
            if move_type == "get":
                # defer deletion until pickup processing finishes
                self.db._deposited = True
            else:
                # moves without `get` (like `give`) can be cleaned up immediately
                self.delete()

    def at_post_move(self, source_location, **kwargs):
        """Alias for at_after_move for compatibility."""
        self.at_after_move(source_location, **kwargs)

    def at_get(self, getter, **kwargs):
        """Delete after being picked up if already deposited."""
        if self.db._deposited:
            self.delete()


class Corpse(Object):
    """A dead body left behind after a character dies."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.display_priority = "corpse"
        if getattr(self.db, "weight", None) is None:
            weight = 0
            if self.db.corpse_of and self.location:
                for obj in self.location.contents:
                    if obj.key == self.db.corpse_of:
                        weight = getattr(obj.db, "weight", 0)
                        break
            self.db.weight = weight
        if (decay := self.db.decay_time):
            # start auto-decay timer in minutes
            self.scripts.add(
                "typeclasses.scripts.AutoDecayScript",
                key="auto_decay",
                interval=int(decay) * 60,
                start_delay=True,
            )

    def at_object_post_creation(self):
        super().at_object_post_creation()
        name = self.db.corpse_of or self.key or "someone"
        self.db.desc = f"The corpse of {name} lies here."

    def get_display_name(self, looker, **kwargs):
        name = self.db.corpse_of or self.key or "corpse"
        return f"the corpse of {name}"

