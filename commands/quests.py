from evennia import CmdSet, create_object
from evennia.utils.utils import make_iter

from .command import Command
from world.quests import Quest, QuestManager


class CmdQCreate(Command):
    """Create and register a quest."""

    key = "qcreate"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: qcreate <quest_key> \"<title>\"")
            return
        parts = self.args.split(None, 1)
        quest_key = parts[0]
        title = parts[1].strip("\"") if len(parts) > 1 else ""
        _, quest = QuestManager.find(quest_key)
        if quest:
            self.msg("Quest already exists.")
            return
        quest = Quest(quest_key=quest_key, title=title)
        QuestManager.save(quest)
        self.msg(f"Quest {quest_key} created.")


class CmdQSet(Command):
    """Set quest attributes."""

    key = "qset"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: qset <quest_key> <attribute> <value>")
            return
        parts = self.args.split(None, 2)
        if len(parts) < 3:
            self.msg("Usage: qset <quest_key> <attribute> <value>")
            return
        quest_key, attr, value = parts
        idx, quest = QuestManager.find(quest_key)
        if quest is None:
            self.msg("Unknown quest.")
            return
        if not hasattr(quest, attr):
            self.msg("Unknown attribute.")
            return
        current = getattr(quest, attr)
        if isinstance(current, bool):
            new_val = value.lower() in ("true", "1", "yes", "on")
        elif isinstance(current, int):
            try:
                new_val = int(value)
            except ValueError:
                self.msg("Value must be a number.")
                return
        elif isinstance(current, list):
            new_val = list(make_iter(value))
        elif isinstance(current, dict):
            if ":" not in value:
                self.msg("Dict value must be <key>:<value>")
                return
            k, v = value.split(":", 1)
            try:
                v = int(v)
            except ValueError:
                pass
            current[k] = v
            new_val = current
        else:
            new_val = value
        setattr(quest, attr, new_val)
        QuestManager.update(idx, quest)
        self.msg(f"{attr} set on {quest_key}.")


class CmdQItem(Command):
    """Create a quest item linked to a quest."""

    key = "qitem"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: qitem <quest_key> <item_key>")
            return
        parts = self.args.split(None, 1)
        if len(parts) < 2:
            self.msg("Usage: qitem <quest_key> <item_key>")
            return
        quest_key, item_key = parts
        idx, quest = QuestManager.find(quest_key)
        if quest is None:
            self.msg("Unknown quest.")
            return
        obj = create_object("typeclasses.objects.Object", key=item_key, location=self.caller)
        obj.tags.add("quest_item", category="quest")
        obj.db.quest = quest_key
        self.msg(f"Created {obj.key} for quest {quest_key}.")


class CmdQAssign(Command):
    """Assign a quest to an NPC."""

    key = "qassign"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: qassign <npc_key> <quest_key>")
            return
        parts = self.args.split(None, 1)
        if len(parts) < 2:
            self.msg("Usage: qassign <npc_key> <quest_key>")
            return
        npc_key, quest_key = parts
        npc = self.caller.search(npc_key, global_search=True)
        if not npc or npc.has_account:
            self.msg("Invalid NPC.")
            return
        _, quest = QuestManager.find(quest_key)
        if quest is None:
            self.msg("Unknown quest.")
            return
        qlist = npc.attributes.get("quests", default=[])
        if quest_key not in qlist:
            qlist.append(quest_key)
        npc.db.quests = qlist
        npc.tags.add("quest_giver", category="role")
        self.msg(f"{npc.key} now offers: {', '.join(qlist)}")


class CmdQTag(Command):
    """Tag quests with guild point rewards."""

    key = "qtag"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: qtag <quest_key> guild <guild_name> <gp_value>")
            return
        parts = self.args.split(None, 3)
        if len(parts) != 4 or parts[1].lower() != "guild":
            self.msg("Usage: qtag <quest_key> guild <guild_name> <gp_value>")
            return
        quest_key, _, guild_name, gp_value = parts
        idx, quest = QuestManager.find(quest_key)
        if quest is None:
            self.msg("Unknown quest.")
            return
        try:
            gp_value = int(gp_value)
        except ValueError:
            self.msg("GP value must be a number.")
            return
        if not getattr(quest, "guild_points", None):
            quest.guild_points = {}
        quest.guild_points[guild_name] = gp_value
        QuestManager.update(idx, quest)
        self.msg(f"{guild_name} awards {gp_value} GP for {quest_key}.")


class QuestCmdSet(CmdSet):
    """CmdSet for quest builder commands."""

    key = "Quest CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdQCreate)
        self.add(CmdQSet)
        self.add(CmdQItem)
        self.add(CmdQAssign)
        self.add(CmdQTag)
