"""
Room

Rooms are simple containers that have no location of their own.
"""

from evennia import create_object
from evennia.utils import iter_to_str, logger, lazy_property
from utils import ansi_pad
from evennia.objects.objects import DefaultRoom
from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
from evennia.contrib.grid.wilderness.wilderness import WildernessRoom
from evennia.objects.models import ObjectDB

from .objects import ObjectParent
from .scripts import RestockScript
from world.triggers import TriggerManager
from utils.mob_utils import mobprogs_to_triggers

from commands.shops import ShopCmdSet
from commands.skills import TrainCmdSet


class RoomParent(ObjectParent):
    """Mixin with logic shared by all rooms."""

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
        return TriggerManager(self, attr="room_triggers")

    def check_triggers(self, event, **kwargs):
        self.trigger_manager.check(event, **kwargs)

    def at_object_receive(self, mover, source_location, move_type=None, **kwargs):
        super().at_object_receive(mover, source_location, **kwargs)
        if "character" in mover._content_types:
            for obj in self.contents_get(content_type="character"):
                if obj != mover:
                    obj.at_character_arrive(mover, **kwargs)
        self.check_triggers("on_enter", obj=mover, source=source_location)

    def at_object_leave(self, mover, destination, **kwargs):
        super().at_object_leave(mover, destination, **kwargs)
        from combat.round_manager import CombatRoundManager
        manager = CombatRoundManager.get()
        if instance := manager.get_combatant_combat(mover):
            instance.remove_combatant(mover)
        if "character" in mover._content_types:
            for obj in self.contents_get(content_type="character"):
                if obj != mover:
                    obj.at_character_depart(mover, destination, **kwargs)
        self.check_triggers("on_leave", obj=mover, destination=destination)

    def set_area(self, area, room_id=None):
        self.db.area = area
        if room_id is not None:
            try:
                self.db.room_id = int(room_id)
            except (TypeError, ValueError):
                self.db.room_id = None

    def get_area(self):
        return self.db.area

    def set_room_id(self, room_id):
        try:
            self.db.room_id = int(room_id)
        except (TypeError, ValueError):
            self.db.room_id = None

    def get_room_id(self):
        return self.db.room_id

    def set_coord(self, x, y):
        try:
            self.db.coord = (int(x), int(y))
        except (TypeError, ValueError):
            self.db.coord = None

    def get_coord(self):
        return self.db.coord

    def get_display_name(self, looker, **kwargs):
        name = self.key
        room_id = self.get_room_id()
        if room_id is not None and looker and (
            looker.check_permstring("Builder") or looker.check_permstring("Admin")
        ):
            area = self.get_area()
            if area:
                name = f"{name} ({area}) - {room_id}"
            else:
                name = f"{name} - {room_id}"
        return name

    def get_display_title(self, looker):
        """Return the formatted room title used when displaying the room."""

        title = self.key
        if looker and (
            looker.check_permstring("Builder") or looker.check_permstring("Admin")
        ):
            area = self.get_area()
            room_id = self.get_room_id()
            bits = []
            if area:
                bits.append(str(area))
            if room_id is not None:
                bits.append(f"[vnum: {room_id}]")
            if bits:
                title = f"{title} |w({' '.join(bits)})|n"
        return title

    def get_display_footer(self, looker, **kwargs):
        cmd_keys = [
            f"|w{cmd.key}|n"
            for cmdset in self.cmdset.all()
            for cmd in cmdset
            if cmd.access(looker, "cmd")
        ]
        return f"Special commands here: {', '.join(cmd_keys)}" if cmd_keys else ""

    def get_display_exits(self, looker, **kwargs):
        exit_names = [key.capitalize() for key in (self.db.exits or {})]
        return "|wExits:|n " + ", ".join(exit_names) if exit_names else "|wExits:|n None"

    def return_appearance(self, looker):
        if not looker:
            return ""

        title = self.get_display_title(looker)
        text = f"|c{title}|n\n{self.db.desc}\n"
        text += f"\n{self.get_display_exits(looker)}"

        visible = [
            obj
            for obj in self.contents
            if obj != looker
            and obj.access(looker, "view")
            and (not hasattr(looker, "can_see") or looker.can_see(obj))
            and not getattr(obj.db, "dead", False)
            and not getattr(obj.db, "_dead", False)
        ]

        characters = [
            obj for obj in visible
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
    def at_object_creation(self):
        super().at_object_creation()
        if self.db.coord is None:
            self.db.coord = (0, 0)

    def generate_map(self, looker):
        coord = self.db.coord or (0, 0)
        x, y = coord
        map_lines = []

        for row_y in range(y + 1, y - 2, -1):
            row = []
            for col_x in range(x - 1, x + 2):
                if (col_x, row_y) == (x, y):
                    symbol = "|g@|n"
                elif (row_y == y and abs(col_x - x) == 1) or (col_x == x and abs(row_y - y) == 1):
                    room_exists = bool(ObjectDB.objects.get_by_attribute(key="coord", value=(col_x, row_y)))
                    symbol = "|g#|n" if room_exists else ""
                else:
                    symbol = ""
                row.append(ansi_pad(symbol, 3))
            map_lines.append("".join(row))

        return "\n".join(map_lines)

    def return_appearance(self, looker):
        appearance = super().return_appearance(looker)
        minimap = self.generate_map(looker)
        return f"{minimap}\n{appearance}" if minimap else appearance

    def get_display_header(self, looker, **kwargs):
        area = self.get_area()
        room_id = self.get_room_id()
        header = []
        if area:
            header.append(str(area))
        if room_id is not None:
            header.append(f"#{room_id}")
        return " ".join(header)


class OverworldRoom(RoomParent, WildernessRoom):
    def get_display_header(self, looker, **kwargs):
        if not self.ndb.minimap:
            self.ndb.minimap = self.db.minimap
        return self.ndb.minimap or ""

    def at_server_reload(self, **kwargs):
        self.db.desc = self.ndb.active_desc
        self.db.minimap = self.ndb.minimap


class XYGridRoom(RoomParent, XYZRoom):
    def at_object_creation(self):
        super().at_object_creation()
        x, y, _ = self.xyz
        try:
            self.db.coord = (int(x), int(y))
        except (TypeError, ValueError):
            self.db.coord = None

    def get_display_header(self, looker, **kwargs):
        x, y, z = self.xyz
        return f"({x}, {y}, {z})"


class XYGridShop(XYGridRoom):
    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(ShopCmdSet, persistent=True)
        self.db.storage = create_object(
            key="shop storage",
            locks="view:perm(Builder);get:perm(Builder);search:perm(Builder)",
            home=self,
            location=self,
        )
        self.scripts.add(RestockScript, key="restock", autostart=False)
        if self.db.inventory:
            script = self.scripts.get("restock")[0]
            script.start()

    def at_init(self):
        super().at_init()
        if self.db.inventory and (script := self.scripts.get("restock")):
            script = script[0]
            if not script.is_active:
                script.start()

    def check_purchase(self, buyer, items):
        from utils.currency import to_copper
        total = sum(obj.db.price or 0 for obj in items)
        wallet = buyer.db.coins or {}
        return (False, total) if total <= 0 or to_copper(wallet) < total else (True, total)

    def purchase(self, buyer, items):
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
        if storage := self.db.storage:
            obj.location = storage
            obj.db.price = (obj.db.value or 0) * 2
            return True
        return False


class XYGridTrain(XYGridRoom):
    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(TrainCmdSet, persistent=True)

    def _calc_cost(self, start, increase):
        return int((start + (start + increase)) * (increase + 1) / 2.0)

    def check_training(self, char, levels):
        from commands.skills import SKILL_DICT
        skill_key = self.db.skill_training
        if not skill_key or skill_key not in SKILL_DICT:
            return None, 0
        sessions = char.db.practice_sessions or 0
        return (False, levels) if sessions < levels else (True, levels)

    def train_skill(self, char, levels):
        from commands.skills import SKILL_DICT
        from world.system import stat_manager
        valid, cost = self.check_training(char, levels)
        if valid is None or not valid:
            return False, cost
        skill_key = self.db.skill_training
        skill = char.traits.get(skill_key)
        if not skill:
            char.traits.add(skill_key, trait_type="counter", min=0, max=100, base=0, stat=SKILL_DICT.get(skill_key))
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
    """A room where you can train AND shop!"""
    pass
