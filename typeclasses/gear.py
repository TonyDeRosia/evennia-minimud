from random import choice
from evennia import AttributeProperty
from evennia.utils import logger
from evennia.contrib.game_systems.containers import ContribContainer

from .objects import Object, ClothingObject
from world.system import stat_manager, state_manager
from combat import combat_utils
from utils import roll_dice_string
from world.combat import get_health_description


class BareHand:
    """
    A dummy "object" class that provides basic combat functionality for unarmed combat
    """

    damage = None
    damage_dice = "2d6"
    stamina_cost = 3
    skill = "unarmed"
    name = "fists"
    speed = 2

    def at_pre_attack(self, wielder, **kwargs):
        """
        Validate that this is usable - has ammo, etc.
        """
        # make sure wielder has enough strength left
        if wielder.traits.stamina.value < self.stamina_cost:
            wielder.msg("You are too tired to hit anything.")
            return False
        return True

    def at_attack(self, wielder, target, **kwargs):
        """
        Hit something with your fists!
        """
        if not getattr(target, "traits", None) or not callable(getattr(target, "at_damage", None)):
            if hasattr(wielder, "msg"):
                wielder.msg("You can't attack that.")
            return
        # Determine unarmed damage
        damage = self.damage
        str_val = state_manager.get_effective_stat(wielder, "STR")
        profs = getattr(wielder.db, "proficiencies", {}) or {}
        knows_hth = "Hand-to-Hand" in (wielder.db.skills or [])
        hth_prof = profs.get("Hand-to-Hand", 0)
        if damage is None:
            try:
                if knows_hth:
                    damage = roll_dice_string("1d3") + (str_val // 5) + (hth_prof // 10)
                else:
                    damage = roll_dice_string("1d2")
            except Exception:
                logger.log_err("Invalid dice roll on BareHand")
                damage = 0
        hit_bonus = hth_prof * 0.2 if knows_hth else 0.0

        from world.skills.unarmed_passive import Unarmed, HandToHand
        for cls in (Unarmed, HandToHand):
            if cls.name in (wielder.db.skills or []):
                cls().improve(wielder)
        # subtract the stamina required to use this
        wielder.traits.stamina.current -= self.stamina_cost

        if not stat_manager.check_hit(wielder, target, base=75 + int(hit_bonus)):
            wielder.at_emote(
                f"$conj(swings) $pron(your) {self.name} at $you(target), but $conj(misses).",
                mapping={"target": target},
            )
        else:
            if combat_utils.roll_evade(wielder, target):
                wielder.at_emote(
                    f"$conj(swings) $pron(your) {self.name} at $you(target), but they evade.",
                    mapping={"target": target},
                )
                return
            if combat_utils.roll_parry(wielder, target):
                wielder.at_emote(
                    f"$conj(swings) $pron(your) {self.name}, but $you(target) parry.",
                    mapping={"target": target},
                )
                return
            if combat_utils.roll_block(wielder, target):
                wielder.at_emote(
                    f"$conj(swings) $pron(your) {self.name}, but $you(target) block.",
                    mapping={"target": target},
                )
                return
            crit = stat_manager.roll_crit(wielder, target)
            if crit:
                damage = stat_manager.crit_damage(wielder, damage)
            damage = combat_utils.apply_attack_power(wielder, damage)
            wielder.at_emote(
                f"$conj(hits) $you(target) with $pron(your) {self.name}.",
                mapping={"target": target},
            )
            dealt = target.at_damage(wielder, damage, "bludgeon", critical=crit)
            combat_utils.apply_lifesteal(wielder, dealt)
            if status := getattr(self, "status_effect", None):
                effect, chance = status
                if stat_manager.roll_status(wielder, target, int(chance)):
                    state_manager.add_status_effect(target, effect, 1)
        pass


class MeleeWeapon(Object):
    """
    Weapons that you hit things with
    """

    speed = AttributeProperty(10)

    def is_twohanded(self):
        """Return True if this weapon requires two hands."""
        return (
            bool(self.db.twohanded)
            or self.tags.has("twohanded", category="flag")
            or self.tags.has("two_handed", category="wielded")
        )

    def at_pre_attack(self, wielder, **kwargs):
        """
        Validate that this is usable - has ammo, etc.
        """
        # make sure wielder has enough strength left
        if wielder.traits.stamina.value < self.attributes.get("stamina_cost", 0):
            wielder.msg("You are too tired to use this.")
            return False
        # this can only be used if it's being wielded
        if self not in wielder.wielding:
            wielder.msg(
                f"You must be wielding your {self.get_display_name(wielder)} to attack with it."
            )
            return False
        else:
            return True

    def at_attack(self, wielder, target, **kwargs):
        """
        Use this weapon in an attack against a target.
        """
        if not getattr(target, "traits", None) or not callable(getattr(target, "at_damage", None)):
            if hasattr(wielder, "msg"):
                wielder.msg("You can't attack that.")
            return
        # get the weapon's damage bonus
        damage = 0
        damage_type = None
        if (dmg_map := getattr(self.db, "damage", None)):
            for i, (dtype, formula) in enumerate(dmg_map.items()):
                try:
                    damage += roll_dice_string(str(formula))
                except Exception:
                    logger.log_err(f"Invalid damage formula '{formula}' on {self}")
                if i == 0:
                    damage_type = dtype
        else:
            if dice := getattr(self.db, "damage_dice", None):
                try:
                    dice_num, dice_sides = map(int, str(dice).lower().split("d"))
                except (TypeError, ValueError):
                    logger.log_err(f"Invalid damage_dice '{dice}' on {self}")
                    damage = int(self.db.dmg or 0)
                else:
                    damage = combat_utils.roll_damage((dice_num, dice_sides))
            else:
                damage = int(self.db.dmg or 0)
            if damage_types := self.tags.get(category="damage_type", return_list=True):
                damage_type = choice(damage_types)

        # does this require skill to use?
        if skill := self.tags.get(category="skill_class"):
            # use the skill
            result = wielder.use_skill(skill, speed=self.speed)
            # apply the weapon damage as a modifier
            damage = damage * result
        # if no skill required, we are just using our unmodified damage value

        # subtract the stamina required to use this
        wielder.traits.stamina.current -= self.attributes.get("stamina_cost", 0)
        if not stat_manager.check_hit(wielder, target):
            wielder.at_emote(
                "$conj(swings) $pron(your) {weapon} at $you(target), but $conj(misses).",
                mapping={"target": target, "weapon": self},
            )
        else:
            if combat_utils.roll_evade(wielder, target):
                wielder.at_emote(
                    "$conj(swings) $pron(your) {weapon} at $you(target), but they evade.",
                    mapping={"target": target, "weapon": self},
                )
                return
            if combat_utils.roll_parry(wielder, target):
                wielder.at_emote(
                    "$conj(swings) $pron(your) {weapon} at $you(target), but $you(target) parry.",
                    mapping={"target": target, "weapon": self},
                )
                return
            if combat_utils.roll_block(wielder, target):
                wielder.at_emote(
                    "$conj(swings) $pron(your) {weapon} at $you(target), but $you(target) block.",
                    mapping={"target": target, "weapon": self},
                )
                return
            crit = stat_manager.roll_crit(wielder, target)
            if crit:
                damage = stat_manager.crit_damage(wielder, damage)
            damage = combat_utils.apply_attack_power(wielder, damage)
            wielder.at_emote(
                "$conj(hits) $you(target) with $pron(your) {weapon}.",
                mapping={"target": target, "weapon": self},
            )
            dealt = target.at_damage(wielder, damage, damage_type, critical=crit)
            combat_utils.apply_lifesteal(wielder, dealt)
            if status := getattr(self.db, "status_effect", None):
                effect, chance = status
                if stat_manager.roll_status(wielder, target, int(chance)):
                    state_manager.add_status_effect(target, effect, 1)
        pass


class WearableContainer(ContribContainer, ClothingObject):
    """A container that can be worn like clothing."""

    def wear(self, wearer, wearstyle, quiet=False):
        result = super().wear(wearer, wearstyle, quiet=quiet)
        if result:
            self.db.worn_by = wearer
        return result

    def remove(self, wearer, quiet=False):
        result = super().remove(wearer, quiet=quiet)
        if result:
            self.db.worn_by = None
        return result

    def at_object_receive(self, obj, source_location, **kwargs):
        super().at_object_receive(obj, source_location, **kwargs)
        if wearer := self.db.worn_by:
            wearer.update_carry_weight()

    def at_object_leave(self, obj, destination, **kwargs):
        super().at_object_leave(obj, destination, **kwargs)
        if wearer := self.db.worn_by:
            wearer.update_carry_weight()
