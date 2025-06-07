from evennia import CmdSet, create_object
from evennia.utils.utils import make_iter

from .command import Command
from world.quests import Quest, QuestManager, normalize_quest_key


class CmdQCreate(Command):
    """
    Create and register a new quest. Usage: qcreate <quest_key> "<title>"

    Usage:
        qcreate

    See |whelp qcreate|n for details.
    """

    key = "qcreate"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: qcreate <quest_key> \"<title>\"")
            return
        parts = self.args.split(None, 1)
        quest_key = normalize_quest_key(parts[0])
        title = parts[1].strip("\"") if len(parts) > 1 else ""
        _, quest = QuestManager.find(quest_key)
        if quest:
            self.msg("Quest already exists.")
            return
        quest = Quest(quest_key=quest_key, title=title)
        QuestManager.save(quest)
        self.msg(f"Quest {quest_key} created.")


class CmdQSet(Command):
    """
    Change quest attributes. Usage: qset <quest_key> <attr> <value>

    Usage:
        qset

    See |whelp qset|n for details.
    """

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
        quest_key = normalize_quest_key(quest_key)
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
    """
    Spawn a quest item. Usage: qitem <quest_key> <item_key>

    Usage:
        qitem

    See |whelp qitem|n for details.
    """

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
        quest_key = normalize_quest_key(quest_key)
        idx, quest = QuestManager.find(quest_key)
        if quest is None:
            self.msg("Unknown quest.")
            return
        obj = create_object("typeclasses.objects.Object", key=item_key, location=self.caller)
        obj.tags.add("quest_item", category="quest")
        obj.db.quest = quest_key
        self.msg(f"Created {obj.key} for quest {quest_key}.")


class CmdQAssign(Command):
    """
    Assign a quest to an NPC. Usage: qassign <npc> <quest_key>

    Usage:
        qassign

    See |whelp qassign|n for details.
    """

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
        quest_key = normalize_quest_key(quest_key)
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
    """
    Set guild point rewards on a quest. Usage: qtag <quest_key> guild <guild> <amount>

    Usage:
        qtag

    See |whelp qtag|n for details.
    """

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


class CmdQuestList(Command):
    """
    List quests offered by NPCs here. Usage: questlist

    Usage:
        questlist

    See |whelp questlist|n for details.
    """

    key = "questlist"
    aliases = ("quests",)
    help_category = "General"

    def func(self):
        caller = self.caller
        if not (location := caller.location):
            return
        givers = [
            obj
            for obj in location.contents
            if obj.tags.has("quest_giver", category="role")
        ]
        if not givers:
            self.msg("There are no quest givers here.")
            return

        completed = caller.db.completed_quests or []
        active = caller.db.active_quests or {}
        lines = []
        for npc in givers:
            quests = []
            for qkey in npc.attributes.get("quests", default=[]):
                idx, quest = QuestManager.find(qkey)
                if not quest:
                    continue
                if not quest.repeatable and qkey in completed:
                    continue
                if qkey in active:
                    continue
                title = quest.title or qkey
                quests.append(title)
            if quests:
                lines.append(f"{npc.get_display_name(caller)}: {', '.join(quests)}")

        if not lines:
            self.msg("No available quests here.")
            return
        self.msg("\n".join(lines))


class CmdAcceptQuest(Command):
    """
    Accept a quest. Usage: accept <quest>

    Usage:
        accept

    See |whelp accept|n for details.
    """

    key = "accept"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            self.msg("Usage: accept <quest>")
            return

        quest_key = normalize_quest_key(self.args.strip())
        active = caller.db.active_quests or {}
        if quest_key in active:
            self.msg("You are already on that quest.")
            return

        completed = caller.db.completed_quests or []
        idx, quest = QuestManager.find(quest_key)
        if not quest:
            self.msg("Unknown quest.")
            return
        if not quest.repeatable and quest_key in completed:
            self.msg("You have already completed that quest.")
            return

        giver = None
        if location := caller.location:
            for obj in location.contents:
                if obj.tags.has("quest_giver", category="role") and quest_key in (
                    obj.attributes.get("quests", default=[])
                ):
                    giver = obj
                    break
        if not giver:
            self.msg("No one here offers that quest.")
            return

        active[quest_key] = {"progress": 0}
        caller.db.active_quests = active
        title = quest.title or quest_key
        self.msg(f"You accept the quest '{title}'.")
        if quest.start_dialogue:
            self.msg(quest.start_dialogue)


class CmdQuestProgress(Command):
    """
    Show your progress on active quests. Usage: progress

    Usage:
        progress

    See |whelp progress|n for details.
    """

    key = "progress"
    help_category = "General"

    def func(self):
        caller = self.caller
        active = caller.db.active_quests or {}
        if not active:
            self.msg("You have no active quests.")
            return

        lines = []
        for qkey, data in active.items():
            idx, quest = QuestManager.find(qkey)
            if not quest:
                continue
            progress = data.get("progress", 0)
            if quest.goal_type == "collect":
                progress = len(
                    [obj for obj in caller.contents if obj.db.quest == qkey]
                )
            title = quest.title or qkey
            lines.append(f"{title}: {progress}/{quest.amount}")

        self.msg("\n".join(lines))


class CmdCompleteQuest(Command):
    """
    Turn in a completed quest. Usage: complete <quest>

    Usage:
        complete

    See |whelp complete|n for details.
    """

    key = "complete"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            self.msg("Usage: complete <quest>")
            return

        quest_key = normalize_quest_key(self.args.strip())
        active = caller.db.active_quests or {}
        if quest_key not in active:
            self.msg("You have not accepted that quest.")
            return

        idx, quest = QuestManager.find(quest_key)
        if not quest:
            self.msg("Unknown quest.")
            return

        progress = active[quest_key].get("progress", 0)
        if quest.goal_type == "collect":
            items = [obj for obj in caller.contents if obj.db.quest == quest_key]
            progress = len(items)
        else:
            items = []

        if progress < quest.amount:
            self.msg("You have not completed the objectives yet.")
            return

        # remove quest items if necessary
        for obj in items:
            obj.delete()

        rewards = []
        if quest.xp_reward:
            caller.db.exp = (caller.db.exp or 0) + quest.xp_reward
            rewards.append(f"{quest.xp_reward} XP")

        from utils.currency import to_copper, from_copper, format_wallet
        from evennia.prototypes.spawner import spawn
        from world.guilds import find_guild, update_guild, auto_promote

        for proto in make_iter(quest.items_reward):
            try:
                objs = spawn(proto)
            except Exception:
                continue
            for obj in objs:
                obj.move_to(caller, quiet=True, move_type="get")
                rewards.append(obj.key)

        if quest.currency_reward:
            wallet = caller.db.coins or {}
            total = to_copper(wallet)
            for coin, amount in quest.currency_reward.items():
                total += to_copper({coin: amount})
            caller.db.coins = from_copper(total)
            rewards.append(format_wallet(quest.currency_reward))

        if quest.guild_points:
            for guild, pts in quest.guild_points.items():
                if caller.db.guild == guild:
                    gp_map = caller.db.guild_points or {}
                    total = gp_map.get(guild, 0) + pts
                    gp_map[guild] = total
                    caller.db.guild_points = gp_map
                    idx, gobj = find_guild(guild)
                    if gobj:
                        gobj.members[str(caller.id)] = total
                        update_guild(idx, gobj)
                        auto_promote(caller, gobj)
                    rewards.append(f"{pts} guild points in {guild}")

        completed = caller.db.completed_quests or []
        if quest_key not in completed:
            completed.append(quest_key)
        caller.db.completed_quests = completed
        del active[quest_key]
        caller.db.active_quests = active

        title = quest.title or quest_key
        if rewards:
            self.msg(f"Quest '{title}' completed! You receive: {', '.join(rewards)}.")
        else:
            self.msg(f"Quest '{title}' completed!")
        if quest.complete_dialogue:
            self.msg(quest.complete_dialogue)


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
        self.add(CmdQuestList)
        self.add(CmdAcceptQuest)
        self.add(CmdQuestProgress)
        self.add(CmdCompleteQuest)
