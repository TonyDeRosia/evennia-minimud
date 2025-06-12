"""Custom script typeclasses used by the game."""

from random import randint, choice
from evennia.utils import make_iter, logger
from evennia.scripts.scripts import DefaultScript
from evennia.prototypes.prototypes import PROTOTYPE_TAG_CATEGORY
from evennia.prototypes.spawner import spawn
from .characters import Character


class Script(DefaultScript):
    """Base script typeclass.

    This lightweight subclass mirrors Evennia's ``DefaultScript`` but is
    defined for clarity and future customization.  Having a project-specific
    script parent makes it easy to tag or extend all in-game scripts later on.
    """

    pass


class CombatScript(Script):
    """
    A script intended to be attached to a room when a combat instance starts.

    Manages the combat within the room; assumes all combat has two sides.
    """

    @property
    def teams(self):
        """Return cached combat teams or initialize them."""

        if not self.ndb.teams:
            teams = self.db.teams
            if hasattr(teams, "deserialize"):
                teams = teams.deserialize()

            if (not isinstance(teams, list)) or len(teams) != 2:
                teams = [[], []]
                self.db.teams = teams
            else:
                # ensure each team is a list
                teams = [list(make_iter(t)) if t else [] for t in teams]
                self.db.teams = teams

            self.ndb.teams = teams
        return self.ndb.teams

    @property
    def fighters(self):
        """
        Returns a list of all combatants, regardless of alliance.
        """
        a, b = self.teams
        return [obj for obj in a + b if obj]

    @property
    def active(self):
        """
        Returns a list of all active combatants, regardless of alliance.
        """
        return [
            obj
            for obj in self.fighters
            if not any(obj.tags.has(["unconscious", "dead", "defeated"]))
        ]

    def at_script_creation(self):
        self.db.teams = [[], []]

    def get_team(self, combatant):
        """
        Gets the index of the team containing combatant, or None if combatant is not in this combat
        """
        for i, team in enumerate(self.teams):
            if combatant in team:
                return i
        return None

    def add_combatant(self, combatant, ally=None, enemy=None, **kwargs):
        """
        Add combatant to the combat instance, either to an ally's team or opposing an enemy

        Returns:
            True if combatant is successfully in the combat instance, False if not
        """
        if combatant in self.fighters:
            # already in combat here
            return True

        # if neither ally nor enemy are given, they're not actually fighting anyone
        if not (ally or enemy):
            return False

        # if ally is given, find ally's team
        if ally and (team := self.get_team(ally)):
            # add combatant to ally's team
            self.db.teams[team].append(combatant)
            # reset the cache
            del self.ndb.teams
            from combat.round_manager import CombatRoundManager
            CombatRoundManager.get().add_instance(self)
            return True

        # if enemy is given, find enemy's team
        if enemy and (team := self.get_team(enemy)):
            # since there are only 2 teams, subtracting 1 from the team index will flip to the other team
            team -= 1

            # add combatant to the team
            self.db.teams[team].append(combatant)
            # reset the cache
            del self.ndb.teams
            from combat.round_manager import CombatRoundManager
            CombatRoundManager.get().add_instance(self)
            return True

        # if we got here, then no one provided was in combat already
        # we can only work with this if this is a clean combat instance
        if enemy and not self.fighters:
            # set up new 1v1 teams
            self.db.teams = [[combatant], [enemy]]
            # reset the cache
            del self.ndb.teams
            from combat.round_manager import CombatRoundManager
            CombatRoundManager.get().add_instance(self)
            return True

        # at this point, there are no valid ways to add
        return False

    def remove_combatant(self, combatant, **kwargs):
        """
        Removes a combatant from the combat instance.

        Returns:
            True if combatant is successfully out of combat, False if not
        """
        # get the combatant's team
        team = self.get_team(combatant)
        if team is None:
            # they're already not in combat
            return True

        # remove combatant from their team
        teams = self.db.teams or [[], []]
        if hasattr(teams, "deserialize"):
            teams = teams.deserialize()
        if 0 <= team < len(teams) and combatant in teams[team]:
            teams[team].remove(combatant)

        # ensure two proper list entries remain after the removal
        if not isinstance(teams, list):
            teams = [[], []]
        else:
            teams = [list(make_iter(t)) if t else [] for t in teams]
            while len(teams) < 2:
                teams.append([])

        self.db.teams = teams
        # reset the cache
        del self.ndb.teams

        # grant exp to the other team, if relevant
        if exp := combatant.db.exp_reward:
            from world.system import state_manager

            for obj in self.db.teams[team - 1]:
                obj.msg(f"You gain {exp} experience.")
                obj.db.exp = (obj.db.exp or 0) + exp
                state_manager.check_level_up(obj)
        self.check_victory()
        # remove their combat target if they have one
        del combatant.db.combat_target
        return True

    def check_victory(self):
        """
        Check the combat instance to see if either side has lost

        If one side is victorious, message the remaining members and delete ourself.
        """
        if not (active_fighters := self.active):
            # everyone lost or is gone
            self.delete()
            return

        # ensure we have two valid team lists before iterating
        teams = self.db.teams or [[], []]
        if hasattr(teams, "deserialize"):
            teams = teams.deserialize()
        if not isinstance(teams, list) or len(teams) != 2:
            teams = [[], []]
        team_a = teams[0] or []
        team_b = teams[1] if len(teams) > 1 else []

        # create a filtered list of only active fighters for each team
        team_a = [obj for obj in team_a if obj in active_fighters]
        team_b = [obj for obj in team_b if obj in active_fighters]

        if team_a and team_b:
            # both teams are still active
            return

        # this case shouldn't arise, but as a redundancy, checks if both teams are inactive
        if not team_a and not team_b:
            # everyone lost or is gone
            self.delete()
            return

        # only one team is active at this point; message the winners
        for obj in active_fighters:
            # remove their combat target if they have one
            del obj.db.combat_target
            obj.msg("The fight is over.")

        # say farewell to the combat script!
        self.delete()


def get_or_create_combat_script(location):
    """
    A helper function to find the current combat script in a location, or create
    a new combat script if one isn't already present.

    Args:
        location (Room): The location being checked for a combat instance.

    Returns:
        script (CombatScript): The combat script attached to the given location.
    """
    if not (combat_script := location.scripts.get("combat")):
        # there's no combat instance; start one
        location.scripts.add(CombatScript, key="combat")
        combat_script = location.scripts.get("combat")[0]
        # ensure the script is saved before any modifications occur
        combat_script.save()
    else:
        combat_script = combat_script[0]

    return combat_script


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


class AutoDecayScript(Script):
    """Delete the attached object after a delay."""

    def at_script_creation(self):
        self.key = "auto_decay"
        self.desc = "Automatically delete an object after a delay"
        self.persistent = True

    def at_repeat(self):
        obj = self.obj
        if obj:
            obj.delete()
        self.stop()
