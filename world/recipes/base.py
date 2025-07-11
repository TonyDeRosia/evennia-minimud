from random import randint
from evennia.utils import iter_to_str
from evennia.contrib.game_systems.crafting import CraftingRecipe


class SkillRecipe(CraftingRecipe):
    """
    The base recipe class for implementing skill checks, modified from the example:

    https://www.evennia.com/docs/latest/Contribs/Contrib-Crafting.html#skilled-crafters
    """

    # The skill requirement for the recipe.
    skill = (None, 0)
    exp_gain = 0

    def craft(self, **kwargs):
        """The input is ok. Determine if crafting succeeds"""

        # this is set at initialization
        crafter = self.crafter

        # let's assume the skill is stored directly on the crafter
        # - the skill is 0..100.
        # get our skill requirements
        req_skill, difficulty = self.skill

        # if no requirement is set, just craft
        if not req_skill or not difficulty:
            return super().craft(**kwargs)

        # otherwise, retrieve the skill from the crafter
        crafting_skill = crafter.traits.get(req_skill)
        # if crafter doesn't have the skill
        if not crafting_skill:
            self.msg("You don't know how to make this.")
            return
        # if crafter just isn't good enough
        elif crafting_skill.value < difficulty:
            self.msg(
                "You are not good enough to make this yet. Better keep practicing!"
            )
            return

        from world.system import state_manager

        success_rate = int(crafting_skill.value - difficulty)
        success_rate += state_manager.get_effective_stat(crafter, "craft_bonus")

        # at this point the crafting attempt is considered happening, so subtract mana
        crafter.traits.mana.current -= 5
        # you should get the experience reward regardless of success
        if self.exp_gain:
            from world.system import state_manager
            state_manager.gain_xp(crafter, self.exp_gain, announce=True)
        # implement some randomness - the higher the difference, the lower the chance of failure
        if not randint(0, success_rate):
            self.msg("It doesn't seem to work out. Maybe you should try again?")
            return

        # all is good, craft away
        return super().craft(**kwargs)
