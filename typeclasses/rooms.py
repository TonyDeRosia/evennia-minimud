"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia import create_object
from evennia.utils import iter_to_str, logger, lazy_property
from evennia.objects.objects import DefaultRoom
from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
from evennia.contrib.grid.wilderness.wilderness import WildernessRoom

from .objects import ObjectParent
from .scripts import RestockScript
from world.triggers import TriggerManager
from utils.mob_utils import mobprogs_to_triggers

from commands.shops import ShopCmdSet
from commands.skills import TrainCmdSet


class RoomParent(ObjectParent):
    """Mixin with logic shared by all rooms."""

    # add a blank line after the room description and exits
    appearance_template = (
        "{name}\n{desc}\n\n{exits}\n\n{characters}\n{things}\n{footer}"
    )

    def at_object_creation(self):
        super().at_object_creation()
        self.db.exits = self.db.exits or {}
        if self.db.room_triggers is None:
            self.db.room_triggers = {}

        if self.db.room_programs and not self.db.room_triggers:
            self.db.room_triggers = mobprogs_to_triggers(self.db.room_programs)

        if self.db.room_triggers:
            self.trigger_manager.start_random_triggers()

    @lazy_property
    def trigger_manager(self):
        """Access :class:`~world.triggers.TriggerManager`."""
        return TriggerManager(self, attr="room_triggers")

    def check_triggers(self, event, **kwargs):
        self.trigger_manager.check(event, **kwargs)

    def at_object_receive(self, mover, source_location, move_type=None, **kwargs):
        """
        Apply extra hooks when an object enters this room, so things (e.g. NPCs) can react.
        """
        super().at_object_receive(mover, source_location, **kwargs)
        # only react if the arriving object is a character
        if "character" in mover._content_types:
            for obj in self.contents_get(content_type="character"):
                if obj == mover:
                    # don't react to ourself
                    continue
                obj.at_character_arrive(mover, **kwargs)
        self.check_triggers("on_enter", obj=mover, source=source_location)

    def at_object_leave(self, mover, destination, **kwargs):
        """
        Apply extra hooks when an object enters this room, so things (e.g. NPCs) can react.
        """
        super().at_object_leave(mover, destination, **kwargs)
        from combat.round_manager import CombatRoundManager
        manager = CombatRoundManager.get()
        if instance := manager.get_combatant_combat(mover):
            instance.remove_combatant(mover)
        # only react if the arriving object is a character
        if "character" in mover._content_types:
            for obj in self.contents_get(content_type="character"):
                if obj == mover:
                    # don't react to ourself
                    continue
                obj.at_character_depart(mover, destination, **kwargs)
        self.check_triggers("on_leave", obj=mover, destination=destination)

    # metadata helpers --------------------------------------------------

    def set_area(self, area, room_id=None):
        """Set this room's area and optional id."""
        self.db.area = area
        if room_id is not None:
            try:
                self.db.room_id = int(room_id)
            except (TypeError, ValueError):  # pragma: no cover - guard
                self.db.room_id = None

    def get_area(self):
        """Return this room's area name."""
        return self.db.area

    def set_room_id(self, room_id):
        """Set this room's numeric id inside its area."""
        try:
            self.db.room_id = int(room_id)
        except (TypeError, ValueError):  # pragma: no cover - guard
            self.db.room_id = None

    def get_room_id(self):
        """Return the room id inside its area."""
        return self.db.room_id

    def get_display_footer(self, looker, **kwargs):
        """
        Shows a list of commands available here to the viewer.
        """

        cmd_keys = [
            f"|w{cmd.key}|n"
            for cmdset in self.cmdset.all()
            for cmd in cmdset
            if cmd.access(looker, "cmd")
        ]
        if cmd_keys:
            return f"Special commands here: {', '.join(cmd_keys)}"
        else:
            return ""

    def get_display_exits(self, looker, **kwargs):
        """Return a list of exits visible to ``looker``."""

        exit_names = [key.capitalize() for key in (self.db.exits or {})]
        if exit_names:
            return "|wExits:|n " + ", ".join(exit_names)
        else:
            return "|wExits:|n None"

    def return_appearance(self, looker):
        if not looker:
            return ""

        text = f"|c{self.key}|n\n"
        text += f"{self.db.desc}\n"

        exits = self.get_display_exits(looker)
        if exits:
            text += f"\n{exits}"

        visible = [
            obj
            for obj in self.contents
            if obj != looker
            and obj.access(looker, "view")
            and (
                not hasattr(looker, "can_see")
                or looker.can_see(obj)
            )
        ]

        characters = [
            obj
            for obj in visible
            if obj.is_typeclass("typeclasses.npcs.NPC", exact=False)
            or obj.is_typeclass("typeclasses.characters.Character", exact=False)
        ]
        in_combat_present = any(getattr(c, "in_combat", False) for c in characters)

        env_objects, npcs, items, players = [], [], [], []
        for obj in visible:
            if obj.db.display_priority == "environment":
                env_objects.append(obj.get_display_name(looker))
                continue

            tag = ""
            if in_combat_present and (
                obj.is_typeclass("typeclasses.npcs.NPC", exact=False)
                or obj.is_typeclass("typeclasses.characters.Character", exact=False)
            ):
                if getattr(obj, "in_combat", False) and obj.db.combat_target:
                    target_name = obj.db.combat_target.get_display_name(looker)
                    tag = f" [fighting {target_name}]"
                else:
                    tag = " [idle]"

            if obj.is_typeclass("typeclasses.npcs.NPC", exact=False):
                npcs.append(f"{obj.return_appearance(looker, room=True)}{tag}")
            elif obj.is_typeclass("typeclasses.characters.Character", exact=False):
                players.append(f"{obj.get_display_name(looker)}{tag}")
            else:
                items.append(obj.get_display_name(looker))

        for category in (env_objects, npcs, items, players):
            if category:
                text += "\n" + "\n".join(category)

        footer = self.get_display_footer(looker)
        if footer:
            text += f"\n{footer}"
        if looker != self:
            self.check_triggers("on_look", looker=looker)
        return text.strip()


class Room(RoomParent, DefaultRoom):
    """Basic indoor room with simple area metadata."""

    def get_display_header(self, looker, **kwargs):
        """Show the area name/room id if available."""
        area = self.get_area()
        room_id = self.get_room_id()
        header = []
        if area:
            header.append(str(area))
        if room_id is not None:
            header.append(f"#{room_id}")
        return " ".join(header)


class OverworldRoom(RoomParent, WildernessRoom):
    """
    A subclass of the Wilderness contrib's room, applying the local RoomParent mixin
    """

    def get_display_header(self, looker, **kwargs):
        """
        Displays a minimap above the room description, if there is one.
        """
        if not self.ndb.minimap:
            self.ndb.minimap = self.db.minimap
        return self.ndb.minimap or ""

    def at_server_reload(self, **kwargs):
        """
        Saves the current ndb desc to db so it's still available after a reload
        """
        self.db.desc = self.ndb.active_desc
        self.db.minimap = self.ndb.minimap


class XYGridRoom(RoomParent, XYZRoom):
    """Room used inside the XYZGrid system."""

    def get_display_header(self, looker, **kwargs):
        """Return the room's XYZ coordinates."""
        x, y, z = self.xyz
        return f"({x}, {y}, {z})"


class XYGridShop(XYGridRoom):
    """
    A grid-aware room that has built-in shop-related functionality.
    """

    def at_object_creation(self):
        """
        Initialize the shop inventory and commands
        """
        super().at_object_creation()
        # add the shopping commands to the room
        self.cmdset.add(ShopCmdSet, persistent=True)
        # create an invisible, inaccessible storage object
        self.db.storage = create_object(
            key="shop storage",
            locks="view:perm(Builder);get:perm(Builder);search:perm(Builder)",
            home=self,
            location=self,
        )
        # attach restocking script if we have an inventory defined
        self.scripts.add(RestockScript, key="restock", autostart=False)
        if self.db.inventory:
            script = self.scripts.get("restock")[0]
            script.start()

    def at_init(self):
        """Ensure restocking runs when the room is loaded."""
        super().at_init()
        if self.db.inventory and (script := self.scripts.get("restock")):
            script = script[0]
            if not script.is_active:
                script.start()

    def check_purchase(self, buyer, items):
        """Validate ``buyer`` can afford ``items``.

        Returns a tuple ``(can_buy, total_cost)``.
        """
        from utils.currency import to_copper

        total = sum(obj.db.price or 0 for obj in items)
        wallet = buyer.db.coins or {}
        if total <= 0 or to_copper(wallet) < total:
            return False, total
        return True, total

    def purchase(self, buyer, items):
        """Handle purchase transaction of ``items`` by ``buyer``."""
        from utils.currency import to_copper, from_copper

        valid, total = self.check_purchase(buyer, items)
        if not valid:
            return False, total

        wallet = buyer.db.coins or {}
        buyer.db.coins = from_copper(to_copper(wallet) - total)
        for obj in items:
            obj.move_to(buyer, quiet=True, move_type="get")
        return True, total

    def add_stock(self, obj):
        """
        Adds new objects to the shop's sale stock
        """
        if storage := self.db.storage:
            # only do this if there's a storage location set
            obj.location = storage
            # price is double the sale value
            val = obj.db.value or 0
            obj.db.price = val * 2
            return True
        else:
            return False


class XYGridTrain(XYGridRoom):
    """
    A grid-aware room that has built-in shop-related functionality.
    """

    def at_object_creation(self):
        """
        Initialize the shop inventory and commands
        """
        super().at_object_creation()
        # add the shopping commands to the room
        self.cmdset.add(TrainCmdSet, persistent=True)

    def _calc_cost(self, start, increase):
        """Return EXP cost for raising a skill."""
        return int((start + (start + increase)) * (increase + 1) / 2.0)

    def check_training(self, char, levels):
        """Validate training request.

        Returns ``(can_train, cost)`` or ``(None, 0)`` if invalid skill.
        """
        from commands.skills import SKILL_DICT

        skill_key = self.db.skill_training
        if not skill_key or skill_key not in SKILL_DICT:
            return None, 0

        sessions = char.db.practice_sessions or 0
        if sessions < levels:
            return False, levels
        return True, levels

    def train_skill(self, char, levels):
        """Apply practice sessions and raise proficiency."""
        from commands.skills import SKILL_DICT
        from world.system import stat_manager

        valid, cost = self.check_training(char, levels)
        if valid is None or valid is False:
            return False, cost

        skill_key = self.db.skill_training
        skill = char.traits.get(skill_key)
        if not skill:
            char.traits.add(
                skill_key,
                trait_type="counter",
                min=0,
                max=100,
                base=0,
                stat=SKILL_DICT.get(skill_key),
            )
            skill = char.traits.get(skill_key)
            skill.proficiency = 25
            char.db.practice_sessions -= 1
            stat_manager.refresh_stats(char)
            return True, 1, skill.proficiency
        prof = getattr(skill, "proficiency", 0)
        spent = 0
        while spent < levels and prof < 75 and char.db.practice_sessions > 0:
            prof = min(75, prof + 25)
            spent += 1
            char.db.practice_sessions -= 1
        skill.proficiency = prof
        stat_manager.refresh_stats(char)
        return True, spent, prof


class XYZShopNTrain(XYGridTrain, XYGridShop):
    """
    A room where you can train AND shop!
    """

    pass
