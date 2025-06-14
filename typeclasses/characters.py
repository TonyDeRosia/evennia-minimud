from random import randint, choice
from string import punctuation
from evennia import AttributeProperty
from evennia import create_object
from evennia.utils import lazy_property, iter_to_str, delay, logger
from evennia.contrib.rpg.traits import TraitHandler
from evennia.contrib.game_systems.clothing.clothing import (
    ClothedCharacter,
    get_worn_clothes,
)
from evennia.contrib.game_systems.cooldowns import CooldownHandler
from evennia.prototypes.spawner import spawn
from utils.currency import to_copper, from_copper, format_wallet
from utils import normalize_slot
from utils.mob_utils import make_corpse
from utils.slots import SLOT_ORDER
from collections.abc import Mapping
import math
from world.triggers import TriggerManager
from world.spells import Spell
from combat.combat_actions import CombatResult
from world.combat import get_health_description
from combat import combat_utils

from .objects import ObjectParent
from world.mob_constants import BODYPARTS

_IMMOBILE = ("sitting", "lying down", "unconscious", "sleeping")

# base stamina cost of moving between rooms
_MOVE_SP_BASE = 1


class Character(ObjectParent, ClothedCharacter):
    """
    The base typeclass for all characters, both player characters and NPCs
    """

    gender = AttributeProperty("plural")
    guild = AttributeProperty("")
    guild_points = AttributeProperty({})
    guild_rank = AttributeProperty("")
    stat_overrides = AttributeProperty({})
    spells = AttributeProperty([])
    training_points = AttributeProperty(0)
    practice_sessions = AttributeProperty(0)

    @property
    def in_combat(self):
        """Return True if in combat, otherwise False"""
        if not (location := self.location):
            # can't be in combat if we're nowhere!
            return False
        if not (combat_script := location.scripts.get("combat")):
            # there is no combat instance in this location
            return False

        # return whether we're in the combat instance's combatants
        return self in combat_script[0].fighters

    @property
    def can_flee(self):
        """
        Calculates chance of escape.

        Returns:
            True if you can flee, otherwise False
        """
        # use dexterity as a fallback for unskilled
        from world.system import state_manager

        if not (evade := self.use_skill("evasion")):
            evade = state_manager.get_effective_stat(self, "DEX")
        # if you have more mana, you can escape more easily
        if (randint(0, 99) - self.traits.mana.value) < evade:
            return True
        else:
            self.msg("You can't find an opportunity to escape.")
            return False

    @lazy_property
    def traits(self):
        # this adds the handler as .traits
        return TraitHandler(self)

    @lazy_property
    def cooldowns(self):
        return CooldownHandler(self, db_attribute="cooldowns")

    @property
    def hp(self):
        """Current health points."""
        hp_trait = getattr(self.traits, "health", None)
        if hp_trait:
            return hp_trait.current
        return 0

    @hp.setter
    def hp(self, value: int) -> None:
        hp_trait = getattr(self.traits, "health", None)
        if hp_trait:
            hp_trait.current = value

    @property
    def max_hp(self):
        """Maximum health points."""
        hp_trait = getattr(self.traits, "health", None)
        if hp_trait:
            return hp_trait.max
        return 0

    @max_hp.setter
    def max_hp(self, value: int) -> None:
        hp_trait = getattr(self.traits, "health", None)
        if hp_trait:
            hp_trait.max = value

    @property
    def wielding(self):
        """Access a list of all wielded objects"""
        return [obj for obj in self.attributes.get("_wielded", {}).values() if obj]

    @property
    def free_hands(self):
        return [
            key for key, val in self.attributes.get("_wielded", {}).items() if not val
        ]

    @property
    def equipment(self):
        """Return mapping of equipment slots to worn or wielded items."""
        # initialize dictionary with all canonical slots so lookups always
        # succeed even if nothing is equipped in a given location
        eq = {slot: None for slot in SLOT_ORDER}

        # start from any stored equipment mapping
        stored = self.db.equipment
        if not isinstance(stored, Mapping):
            stored = {}
        for slot, item in stored.items():
            canonical = normalize_slot(slot) or slot
            eq[canonical] = item

        # fall back to worn clothes for legacy items not stored in db.equipment
        for item in get_worn_clothes(self):
            if item in eq.values():
                continue
            slots = item.tags.get(category="slot", return_list=True) or []
            if not slots and (ctype := item.db.clothing_type):
                slots = [ctype]
            for slot in slots:
                if slot:
                    canonical = normalize_slot(slot)
                    if canonical and not eq.get(canonical):
                        eq[canonical] = item

        # merge wielded weapons
        wielded = self.attributes.get("_wielded", {})
        if wielded:
            wielded.deserialize()

        main = self.db.handedness or "right"
        off = "left" if main == "right" else "right"

        eq["mainhand"] = wielded.get(main)
        eq["offhand"] = wielded.get(off)

        return eq

    # -------------------------------------------------------------
    # Carry weight helpers
    # -------------------------------------------------------------

    def update_carry_weight(self):
        """Recalculate and store total weight of carried items."""
        weight = 0
        for obj in self.contents:
            if obj.db.worn:
                continue
            w = getattr(obj.db, "weight", 0)
            weight += w if isinstance(w, (int, float)) else 0
        self.db.carry_weight = weight

    def encumbrance_level(self):
        """Return a text description of current encumbrance."""
        capacity = self.db.carry_capacity or 0
        weight = self.db.carry_weight or 0
        if capacity <= 0 or weight <= capacity:
            return ""
        if weight <= 1.5 * capacity:
            return "Encumbered (Light)"
        if weight <= 2.0 * capacity:
            return "Encumbered (Moderate)"
        return "Encumbered (Severe)"

    # -------------------------------------------------------------
    # Visibility helpers
    # -------------------------------------------------------------

    def can_see(self, target) -> bool:
        """Return ``True`` if ``self`` can see ``target``."""

        if target == self:
            return True

        # blindness overrides everything
        if self.tags.get("blind", category="status"):
            return False

        # check room darkness
        location = getattr(self, "location", None)
        if location and location.tags.get("dark", category="status"):
            if not self.tags.get("infrared", category="status"):
                return False

        # invisible targets require detect_invis
        if target.tags.get("invisible", category="status"):
            if not self.tags.get("detect_invis", category="status"):
                return False

        # hidden targets require detect_hidden
        if target.tags.get("hidden", category="status"):
            if not self.tags.get("detect_hidden", category="status"):
                return False

        return True

    def defense(self, damage_type=None):
        """
        Get the total armor defense from equipped items and natural defenses

        The damage_type keyword is unused by default.
        """
        return sum(
            [obj.attributes.get("armor", 0) for obj in get_worn_clothes(self) + [self]]
        )

    def at_object_creation(self):
        from world import stats
        from world.system import stat_manager

        # Apply all default stats in a single modular step. If stats already
        # exist on the character, `apply_stats` will not overwrite them.
        stats.apply_stats(self)
        stat_manager.refresh_stats(self)

        # Mark character as tickable so the global tick script processes it
        self.tags.add("tickable")

        self.db.guild = ""
        self.db.guild_points = {}
        self.db.guild_rank = ""
        self.db.stat_overrides = {}
        self.db.equip_bonuses = {}
        self.db.spells = []
        self.db.training_points = 0
        self.db.practice_sessions = 0
        from django.conf import settings
        self.db.level = 1
        self.db.experience = 0
        self.db.tnl = settings.XP_PER_LEVEL
        self.db.sated = 5

    def at_post_puppet(self, **kwargs):
        """Ensure stats refresh when a character is controlled."""
        from world import stats
        from world.system import stat_manager

        stats.apply_stats(self)
        stat_manager.recalculate_stats(self)

    def at_object_receive(self, obj, source_location, **kwargs):
        """Update carry weight when gaining an item."""
        super().at_object_receive(obj, source_location, **kwargs)
        self.update_carry_weight()

    def at_object_leave(self, obj, target_location, **kwargs):
        """Handle cleanup when an object leaves our inventory."""
        super().at_object_leave(obj, target_location, **kwargs)
        from world.system import stat_manager

        # check if this object was equipped when removed
        if obj in self.wielding:
            # clear from wielded mapping without moving it back
            wielded = self.attributes.get("_wielded", {})
            if wielded:
                wielded.deserialize()
            for hand, weap in list(wielded.items()):
                if weap == obj:
                    wielded[hand] = None
            self.db._wielded = wielded
            stat_manager.remove_item_bonuses(self, obj)
        elif obj in self.equipment.values():
            # remove worn item from equipment mapping
            obj.db.worn = False
            eq = self.db.equipment or {}
            for slot, itm in list(eq.items()):
                if itm == obj:
                    eq.pop(slot, None)
                    break
            self.db.equipment = eq
            stat_manager.remove_item_bonuses(self, obj)

        self.update_carry_weight()
        stat_manager.refresh_stats(self)

    def at_pre_move(self, destination, **kwargs):
        """
        Called by self.move_to when trying to move somewhere. If this returns
        False, the move is immediately cancelled.
        """
        if self.tags.has("stationary", category="flag"):
            self.msg("You cannot move.")
            return False
        # check if we have any statuses that prevent us from moving
        if statuses := self.tags.get(_IMMOBILE, category="status", return_list=True):
            self.msg(
                f"You can't move while you're {iter_to_str(sorted(statuses), endsep='or')}."
            )
            return False

        # check if we're in combat
        if self.in_combat:
            self.msg("You can't leave while in combat.")
            return False

        return super().at_pre_move(destination, **kwargs)

    def at_post_move(self, source_location, **kwargs):
        """
        optional post-move auto prompt
        """
        super().at_post_move(source_location, **kwargs)
        self.update_carry_weight()

        carry_capacity = self.db.carry_capacity or 0
        carry_weight = self.db.carry_weight or 0
        cost = _MOVE_SP_BASE
        if carry_weight > carry_capacity and carry_capacity > 0:
            excess = carry_weight - carry_capacity
            cost += excess // 10
        if self.tags.has("hungry_thirsty", category="status"):
            cost += 1
        if self.traits.stamina:
            self.traits.stamina.current = max(self.traits.stamina.current - cost, 0)

        # check if we have auto-prompt in settings
        if self.account and (settings := self.account.db.settings):
            if settings.get("auto prompt"):
                status = self.get_display_status(self)
                self.msg(prompt=status)

    def at_damage(self, attacker, damage, damage_type=None, critical=False):
        """
        Apply damage, after taking into account damage resistances.
        """
        from combat.damage_types import (
            DamageType,
            ResistanceType,
            get_damage_multiplier,
        )

        from world.system import state_manager
        from evennia.utils import utils

        # apply armor damage reduction with piercing
        reduction = self.defense(damage_type)
        if attacker:
            reduction = max(0, reduction - state_manager.get_effective_stat(attacker, "piercing"))
        damage -= reduction
        damage = max(0, damage)
        if attacker:
            log = getattr(self.ndb, "damage_log", None) or {}
            log[attacker] = log.get(attacker, 0) + int(damage)
            self.ndb.damage_log = log

        dt = None
        if damage_type:
            try:
                dt = DamageType(damage_type)
            except ValueError:
                dt = None

        if dt:
            resist_values = getattr(self.db, "resistances", []) or []
            resistances = [
                ResistanceType(r)
                for r in resist_values
                if r in ResistanceType._value2member_map_
            ]
            damage = int(damage * get_damage_multiplier(resistances, dt))

        # magic resist mitigation
        if dt and dt not in (DamageType.SLASHING, DamageType.PIERCING, DamageType.BLUDGEONING):
            mres = state_manager.get_effective_stat(self, "magic_resist")
            if attacker:
                mres -= state_manager.get_effective_stat(attacker, "spell_penetration")
            if mres > 0:
                damage = max(0, damage - mres)


        self.traits.health.current -= damage
        crit_prefix = "|rCritical!|n " if critical else ""
        if attacker:
            self.msg(
                f"{crit_prefix}You take {damage} damage from {attacker.get_display_name(self)}."
            )
            attacker.msg(
                f"You deal {damage} damage to {self.get_display_name(attacker)}"
                + ("!" if critical else ".")
            )
        else:
            self.msg(f"{crit_prefix}You take {damage} damage.")
        if self.traits.health.value <= 0:
            self.tags.add("unconscious", category="status")
            self.tags.add("lying down", category="status")
            self.msg(
                "You fall unconscious. You can |wrespawn|n or wait to be |wrevive|nd."
            )
            if isinstance(attacker, PlayerCharacter):
                bounty = self.db.bounty or 0
                if bounty:
                    wallet = attacker.db.coins or {}
                    total = to_copper(wallet) + bounty
                    attacker.db.coins = from_copper(total)
                    attacker.msg(
                        f"You claim {bounty} bounty coins from {self.get_display_name(attacker)}."
                    )
                    self.msg(
                        f"{attacker.get_display_name(self)} claims your bounty of {bounty} coins."
                    )
                    self.db.bounty = 0
            self.traits.health.rate = 0
            if self.in_combat:
                combat = self.location.scripts.get("combat")[0]
                if not combat.remove_combatant(self):
                    # something went wrong...
                    logger.log_err(
                        f"Could not remove defeated character from combat! Character: {self.name} (#{self.id}) Location: {self.location.name} (#{self.location.id})"
                    )
                    return
            if bounty := self.db.bounty:
                wallet = attacker.db.coins or {}
                total = to_copper(wallet) + bounty
                attacker.db.coins = from_copper(total)
                attacker.msg(f"You claim {bounty} coins for defeating {self.key}.")
                self.db.bounty = 0
            if utils.inherits_from(self, PlayerCharacter):
                self.on_death(attacker)
        return damage
    def at_emote(self, message, **kwargs):
        """
        Execute a room emote as ourself.

        This acts as a wrapper to `self.location.msg_contents` to avoid boilerplate validation.
        """
        # if there is nothing to send or nowhere to send it to, cancel
        if not message or not self.location:
            return
        # add period to punctuation-less emotes
        if message[-1] not in punctuation:
            message += "."
        if kwargs.get("prefix", True) and not message.startswith("$You()"):
            message = f"$You() {message}"
        mapping = kwargs.get("mapping", None)

        self.location.msg_contents(text=message, from_obj=self, mapping=mapping)

    def at_wield(self, weapon, **kwargs):
        """
        Wield a weapon in one or both hands
        """
        # fetch the wielded info and detach from the DB
        wielded = self.attributes.get("_wielded", {})
        if wielded:
            wielded.deserialize()

        # verify flags
        if not weapon.tags.has("equipment", category="flag"):
            self.msg(f"{weapon.get_display_name(self)} can't be wielded.")
            return
        if not weapon.tags.has("identified", category="flag"):
            self.msg(f"You don't know how to use {weapon.get_display_name(self)}.")
            return

        # which hand (or "hand") we'll wield it in
        # get all available hands
        free = self.free_hands

        if hand := kwargs.get("hand"):
            # if a specific hand was requested, free it if occupied
            if hand not in free:
                if not (weap := wielded.get(hand)):
                    self.msg(f"You do not have a {hand}.")
                    return
                self.at_unwield(weap)
                wielded = self.attributes.get("_wielded", {})
                if wielded:
                    wielded.deserialize()
                free = self.free_hands
        elif not free:
            # no free hands - automatically free the main hand weapon
            if weap := next((w for w in wielded.values() if w), None):
                self.at_unwield(weap)
                wielded = self.attributes.get("_wielded", {})
                if wielded:
                    wielded.deserialize()
                free = self.free_hands
            else:
                self.msg(f"Your hands are full.")
                return
        # handle hand restrictions
        main = self.db.handedness or "right"
        off = "left" if main == "right" else "right"

        if weapon.tags.has("mainhand", category="flag"):
            required = main
        elif weapon.tags.has("offhand", category="flag"):
            required = off
        else:
            required = None

        if required:
            if hand and hand != required:
                self.msg(
                    f"{weapon.get_display_name(self)} must be wielded in your {required} hand."
                )
                return
            if required not in free:
                self.msg(f"Your {required} hand is not free.")
                return
            hand = required

        # handle two-handed weapons
        twohanded = getattr(weapon, "is_twohanded", lambda: False)()
        if twohanded:
            if any(
                obj.tags.has("shield", category="flag")
                for obj in get_worn_clothes(self)
            ):
                self.msg(
                    f"You cannot wield {weapon.get_display_name(self)} while using a shield."
                )
                return
            if len(free) < 2:
                # not enough free hands to hold this
                self.msg(
                    f"You need two hands free to wield {weapon.get_display_name(self)}."
                )
                return
            # put the weapon as wielded in the first two hands
            hands = free[:2]
            for h in hands:
                wielded[h] = weapon
        else:
            if not hand:
                # check handedness first, then find a hand
                if main in free:
                    hand = main
                else:
                    hand = free[0]
            # put the weapon as wielded in the hand
            hands = [hand]
            wielded[hand] = weapon

        # update the character with the new wielded info and move the item out of inventory
        self.db._wielded = wielded
        weapon.location = None
        self.update_carry_weight()
        from world.system import stat_manager

        stat_manager.apply_item_bonuses_once(self, weapon)
        # return the list of hands that are now holding the weapon
        return hands

    def at_unwield(self, weapon, **kwargs):
        """
        Stop wielding a weapon
        """
        # fetch the wielded info and detach from the DB
        wielded = self.attributes.get("_wielded", {})
        if wielded:
            wielded.deserialize()

        # can't unwield a weapon you aren't wielding
        if weapon not in wielded.values():
            self.msg("You are not wielding that.")
            return

        # replace weapon with an instance of a bare hand
        freed = []
        for hand, weap in wielded.items():
            if weap == weapon:
                # create a correctly-named fist
                wielded[hand] = None
                # append the hand to the list of freed hands
                freed.append(hand)

        # update the character with the new wielded info and return weapon to inventory
        self.db._wielded = wielded
        weapon.location = self
        self.update_carry_weight()
        from world.system import stat_manager

        stat_manager.remove_item_bonuses(self, weapon)
        # return the list of hands that are no longer holding the weapon
        return freed

    def use_skill(self, skill_name, *args, **kwargs):
        """
        Attempt to use a skill, applying any stat bonus as necessary.
        """
        from world.system import state_manager
        target = kwargs.get("target")

        # using an active combat skill if a target is provided
        if target is not None:
            from combat.combat_skills import SKILL_CLASSES

            skill_cls = SKILL_CLASSES.get(skill_name)
            if not skill_cls:
                return CombatResult(actor=self, target=target, message="Nothing happens.")
            skill = skill_cls()
            if not self.cooldowns.ready(skill.name):
                return CombatResult(actor=self, target=self, message="Still recovering.")
            if self.traits.stamina.current < skill.stamina_cost:
                return CombatResult(actor=self, target=self, message="Too exhausted.")
            self.traits.stamina.current -= skill.stamina_cost
            state_manager.add_cooldown(self, skill.name, skill.cooldown)
            result = skill.resolve(self, target)
            for eff in skill.effects:
                state_manager.add_status_effect(target, eff.key, eff.duration)
            return result

        # passive skill usage
        if not skill_name:
            return 1
        if not (skill_trait := self.traits.get(skill_name)):
            return 0

        stat_bonus = 0
        if stat := getattr(skill_trait, "stat", None):
            stat_bonus = state_manager.get_effective_stat(self, stat)
        prof = getattr(skill_trait, "proficiency", 0)
        if prof < 100:
            skill_trait.proficiency = min(100, prof + 1)
        return skill_trait.value + stat_bonus

    def cast_spell(self, spell_key, target=None):
        """Cast a known spell, spending mana."""
        from world.spells import SPELLS
        from world.system import state_manager

        spell = SPELLS.get(spell_key)
        if not spell:
            return False
        if not self.cooldowns.ready(spell.key):
            return False
        known = self.db.spells or []
        srec = None
        for entry in known:
            if isinstance(entry, str) and entry == spell_key:
                srec = Spell(spell.key, spell.stat, spell.mana_cost, spell.desc, 0)
                idx = known.index(entry)
                known[idx] = srec
                self.db.spells = known
                break
            if hasattr(entry, "key") and entry.key == spell_key:
                srec = entry
                break
        if not srec:
            return False
        if self.traits.mana.current < spell.mana_cost:
            return False
        self.traits.mana.current -= spell.mana_cost
        state_manager.add_cooldown(self, spell.key, spell.cooldown)
        if target:
            self.location.msg_contents(
                f"{self.get_display_name(self)} casts {spell.key} at {target.get_display_name(self)}!"
            )
        else:
            self.location.msg_contents(
                f"{self.get_display_name(self)} casts {spell.key}!"
            )
        if srec.proficiency < 100:
            srec.proficiency = min(100, srec.proficiency + 1)
            self.db.spells = known
        return True

    def get_display_status(self, looker, **kwargs):
        """
        Returns a quick view of the current status of this character
        """

        from world.system import stat_manager

        stat_manager.refresh_stats(self)

        chunks = []
        # prefix the status string with the character's name, if it's someone else checking
        if looker != self:
            chunks.append(self.get_display_name(looker, **kwargs))

        # add resource levels
        hp = int(math.ceil(self.traits.health.percent(None)))
        mp = int(math.ceil(self.traits.mana.percent(None)))
        sp = int(math.ceil(self.traits.stamina.percent(None)))
        chunks.append(f"Health {hp}% : Mana {mp}% : Stamina {sp}%")

        # get all the current status flags for this character
        if status_tags := self.tags.get(category="status", return_list=True):
            # add these statuses to the string, if there are any
            chunks.append(iter_to_str(status_tags))

        if looker == self:
            # if we're checking our own status, include cooldowns
            all_cooldowns = [
                (key, self.cooldowns.time_left(key, use_int=True))
                for key in self.cooldowns.all
            ]
            all_cooldowns = [f"{c[0]} ({c[1]}s)" for c in all_cooldowns if c[1]]
            if all_cooldowns:
                chunks.append(f"Cooldowns: {iter_to_str(all_cooldowns, endsep=',')}")

        # glue together the chunks and return
        return " - ".join(chunks)

    def get_resource_prompt(self):
        """Return the player's prompt string."""
        from world.system import stat_manager

        stat_manager.refresh_stats(self)

        hp_cur = int(self.traits.health.current)
        hp_max = int(self.traits.health.max)
        mp_cur = int(self.traits.mana.current)
        mp_max = int(self.traits.mana.max)
        sp_cur = int(self.traits.stamina.current)
        sp_max = int(self.traits.stamina.max)

        coins = self.db.coins or {}
        data = {
            "hp": hp_cur,
            "hpmax": hp_max,
            "mp": mp_cur,
            "mpmax": mp_max,
            "sp": sp_cur,
            "spmax": sp_max,
            "level": self.db.level or 1,
            "xp": self.db.exp or 0,
            "copper": coins.get("copper", 0),
            "silver": coins.get("silver", 0),
            "gold": coins.get("gold", 0),
            "platinum": coins.get("platinum", 0),
            "carry": self.db.carry_weight or 0,
            "capacity": self.db.carry_capacity or 0,
            "enc": self.encumbrance_level(),
        }

        if fmt := self.db.prompt_format:
            try:
                return fmt.format(**data)
            except Exception as err:  # pragma: no cover - format errors
                logger.log_err(f"Prompt format error for {self}: {err}")

        return (
            f"[|r{hp_cur}|n/{hp_max}] "
            f"[|b{mp_cur}|n/{mp_max}] "
            f"[|g{sp_cur}|n/{sp_max}] >"
        )

    def at_character_arrive(self, chara, **kwargs):
        """
        Respond to the arrival of a character
        """
        if chara == self:
            return

        if self.sessions.count():
            self.refresh_prompt()

        if hasattr(self, "check_triggers"):
            self.check_triggers("char_enter", chara=chara)

    def at_character_depart(self, chara, destination, **kwargs):
        """
        Respond to the departure of a character
        """
        if chara == self:
            return

        if self.sessions.count():
            self.refresh_prompt()

        if hasattr(self, "check_triggers"):
            self.check_triggers("char_leave", chara=chara, destination=destination)

    def at_tick(self):
        """Called by the global ticker.

        Regenerates resources based on current status and refreshes the prompt
        to visually reflect the changes.
        """
        from world.system import state_manager

        state_manager.apply_regen(self)

        if self.sessions.count():
            self.refresh_prompt()

    def refresh_prompt(self):
        """Refresh the player's prompt display."""
        if self.sessions.count():
            self.msg(prompt=self.get_resource_prompt())

    def attack(self, target, weapon, **kwargs):
        """Execute an attack using ``weapon`` against ``target``."""
        if not self.in_combat or self.db.fleeing or self.tags.has("unconscious"):
            return

        if not target:
            if not (target := self.db.combat_target):
                if self.sessions.count():
                    self.msg("You cannot attack nothing.")
                return
        if self.location != target.location:
            if self.sessions.count():
                self.msg("You don't see your target.")
            return

        if not getattr(target, "traits", None) or not callable(getattr(target, "at_damage", None)):
            if self.sessions.count():
                self.msg("You can't attack that.")
            return

        if not (hasattr(weapon, "at_pre_attack") and hasattr(weapon, "at_attack")):
            if self.sessions.count():
                self.msg(f"You cannot attack with {weapon.get_numbered_name(1, self)}.")
            return
        if not weapon.at_pre_attack(self):
            return

        weapon.at_attack(self, target)

        if self.sessions.count():
            self.refresh_prompt()

        if speed := getattr(weapon, "speed", None):
            delay(speed, self.attack, None, weapon, persistent=True)

        if hasattr(self, "check_triggers"):
            self.check_triggers("on_attack", target=target, weapon=weapon)


    def revive(self, reviver, **kwargs):
        """
        Revive a defeated character at partial health.
        """
        # this function receives the actor doing the revive so you could implement your own skill check
        # however, we don't have any relevant skills
        if self.tags.has("unconscious"):
            self.tags.remove("unconscious")
            self.tags.remove("lying down")
            # this sets the current HP to 20% of the max, a.k.a. one fifth
            self.traits.health.current = self.traits.health.max // 5
            self.msg(prompt=self.get_display_status(self))
            self.traits.health.rate = 0.0
            if self.traits.mana:
                self.traits.mana.rate = 0.0
            if self.traits.stamina:
                self.traits.stamina.rate = 0.0


class PlayerCharacter(Character):
    """
    The typeclass for all player characters, including special player-feedback features.
    """

    def at_object_creation(self):
        super().at_object_creation()
        # initialize hands
        self.db._wielded = {"left": None, "right": None}

    def get_display_name(self, looker, **kwargs):
        """
        Adds color to the display name.
        """
        name = super().get_display_name(looker, **kwargs)
        if looker == self:
            # special color for our own name
            return f"|c{name}|n"
        return f"|g{name}|n"

    def at_damage(self, attacker, damage, damage_type=None, critical=False):
        dmg = super().at_damage(attacker, damage, damage_type=damage_type, critical=critical)
        if self.traits.health.value < 50 and self.sessions.count():
            self.refresh_prompt()
        return dmg

    def on_death(self, attacker):
        """Create a corpse with body parts when the player dies."""
        if not self.location:
            return

        # remove from combat if necessary. Victory cleanup may have already
        # deleted the combat script, so ensure it is valid before using it.
        if self.in_combat and (script := self.location.scripts.get("combat")):
            if script and script[0].pk:
                script[0].remove_combatant(self)
        # avoid spawning multiple corpses for repeated calls
        existing = [
            obj
            for obj in self.location.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
            and obj.db.corpse_of == self.key
        ]
        if existing:
            return
        corpse = create_object(
            "typeclasses.objects.Corpse",
            key=f"{self.key} corpse",
            location=self.location,
            attributes=[("corpse_of", self.key), ("is_corpse", True)],
        )
        from world import prototypes

        for part in BODYPARTS:
            proto_name = f"{part.name}_PART"
            proto = getattr(prototypes, proto_name, None)
            if proto:
                obj = spawn(proto)[0]
                obj.location = corpse
            else:
                create_object(
                    "typeclasses.objects.Object",
                    key=part.value,
                    location=corpse,
                )
        self.at_death(attacker)
        self.award_xp_to(attacker)


    def respawn(self):
        """
        Resets the character back to the spawn point with full health.
        """
        self.tags.remove("unconscious", category="status")
        self.tags.remove("lying down", category="status")
        self.traits.health.reset()
        self.traits.health.rate = 0.0
        if self.traits.mana:
            self.traits.mana.rate = 0.0
        if self.traits.stamina:
            self.traits.stamina.rate = 0.0
        self.move_to(self.home)
        self.msg(prompt=self.get_display_status(self))

    def return_appearance(self, looker):
        """Return a description of this player with equipped items."""

        if not looker:
            return ""

        eq_lines = []
        for slot, item in self.equipment.items():
            if not item:
                continue
            if not item.access(looker, "view") or not item.access(looker, "search", default=True):
                continue
            if hasattr(looker, "can_see") and not looker.can_see(item):
                continue
            eq_lines.append(f"|w{slot.capitalize()}|n: {item.get_display_name(looker)}")

        if not eq_lines:
            eq_lines.append("They are not wearing any equipment.")

        eq_text = "\n".join(eq_lines)
        desc = self.db.desc or "You see nothing special."
        return f"{eq_text}\n{desc}"


class NPC(Character):
    """Base typeclass for AI-driven non-player characters.

    NPCs can be assigned roles with ``obj.tags.add("<role>", category="npc_role")``.
    Triggers for reacting to game events are stored in ``db.triggers`` as a
    mapping from event name to one or more trigger definitions. A trigger may
    be a tuple ``(match, reaction)`` or a dictionary with optional ``match`` and
    ``reactions`` keys. See :mod:`world.triggers` for details.
    """

    # defines what color this NPC's name will display in
    name_color = AttributeProperty("w")
    # mapping of event triggers -> reactions
    triggers = AttributeProperty({})

    @lazy_property
    def trigger_manager(self):
        """Access :class:`~world.triggers.TriggerManager`."""
        return TriggerManager(self)

    def at_object_creation(self):
        super().at_object_creation()
        if self.db.triggers is None:
            self.db.triggers = {}
        self.trigger_manager.start_random_triggers()

    def check_triggers(self, event, **kwargs):
        """Evaluate stored triggers for a given event."""
        self.trigger_manager.check(event, **kwargs)

    def at_death(self, killer, **kwargs):
        """Called when character dies."""
        self.check_triggers("death", killer=killer)

    # death handling -----------------------------------------------------

    def drop_loot(self, killer=None):
        """Create a corpse and deposit any drops and coins."""
        from utils.currency import COIN_VALUES
        from utils.prototype_manager import load_prototype

        drops = list(self.db.drops or [])
        coin_loot: dict[str, int] = {}
        if loot_table := self.db.loot_table:
            for entry in loot_table:
                proto = entry.get("proto")
                if not proto:
                    continue
                chance = int(entry.get("chance", 100))
                guaranteed = entry.get("guaranteed_after")
                count = entry.get("_count", 0)
                
                roll = randint(1, 100)
                if roll <= chance or (
                    guaranteed is not None and count >= int(guaranteed)
                ):
                    if isinstance(proto, str) and proto.lower() in COIN_VALUES:
                        amt = int(entry.get("amount", 1))
                        coin_loot[proto.lower()] = coin_loot.get(proto.lower(), 0) + amt
                    else:
                        if isinstance(proto, int) or (isinstance(proto, str) and proto.isdigit()):
                            proto_data = load_prototype("object", int(proto))
                            if proto_data:
                                drops.append(proto_data)
                        else:
                            drops.append(proto)
                    entry["_count"] = 0
                else:
                    entry["_count"] = count + 1

        corpse = make_corpse(self)

        objs = spawn(*drops)
        for obj in objs:
            obj.location = corpse

        # handle coin rewards
        coin_map = {}
        if self.db.coin_drop:
            for coin, amt in (self.db.coin_drop or {}).items():
                coin_map[coin] = coin_map.get(coin, 0) + int(amt)
        for coin, amt in coin_loot.items():
            coin_map[coin] = coin_map.get(coin, 0) + int(amt)

        if coin_map:
            total_copper = to_copper(coin_map)
            if killer:
                wallet = killer.db.coins or {}
                killer.db.coins = from_copper(to_copper(wallet) + total_copper)
                if hasattr(killer, "msg"):
                    killer.msg(f"You receive {format_wallet(from_copper(total_copper))}.")
            else:
                for coin, amt in from_copper(total_copper).items():
                    if amt:
                        pile = create_object(
                            "typeclasses.objects.CoinPile",
                            key=f"{coin} coins",
                            location=corpse,
                        )
                        pile.db.coin_type = coin
                        pile.db.amount = amt

        return corpse

    def award_xp_to(self, attacker):
        """Grant experience reward to ``attacker``."""
        from world.system import state_manager
        exp_reward = getattr(self.db, "exp_reward", 0)
        if exp_reward is None:
            exp_reward = 0
        exp = int(exp_reward)
        if not attacker or not exp:
            return
        if hasattr(attacker, "msg"):
            attacker.msg(f"You gain {exp} experience.")
        state_manager.gain_xp(attacker, exp)

    def on_death(self, attacker):
        """Handle character death cleanup."""
        if not self.location or self.attributes.get("_dead"):
            return
        self.db._dead = True
        self.db.dead = True

        # remove from combat if necessary. The combat script may have been
        # cleaned up already, so verify it before using it.
        if self.in_combat and (script := self.location.scripts.get("combat")):
            if script and script[0].pk:
                script[0].remove_combatant(self)

        corpse = self.drop_loot(attacker)
        if corpse:
            corpse.location = self.location

        self.at_death(attacker)
        if self.location:
            if attacker:
                self.location.msg_contents(
                    f"{self.key} is slain by {attacker.key}!"
                )
            else:
                self.location.msg_contents(f"{self.key} dies.")

        engine = getattr(getattr(self, "ndb", None), "combat_engine", None)
        if engine:
            engine.award_experience(attacker, self)
        else:
            from combat.combat_utils import award_xp

            xp = getattr(self.db, "xp_reward", None)
            if xp is None:
                xp = getattr(self.db, "exp_reward", 0)
            xp = int(xp or 0)
            if not xp:
                level = getattr(self.db, "level", 1) or 1
                xp = level * 5

            log = getattr(getattr(self, "ndb", None), "damage_log", {})
            contributors = list(log.keys()) or ([attacker] if attacker else [])
            contributors = [c for c in contributors if c]
            award_xp(attacker, xp, contributors)
        self.delete()

    # property to mimic weapons
    @property
    def speed(self):
        weapon = self.db.natural_weapon
        if not weapon:
            return 10
        return weapon.get("speed", 10)

    def get_display_name(self, looker, **kwargs):
        """
        Adds color to the display name.
        """
        name = super().get_display_name(looker, **kwargs)
        return f"|{self.name_color}{name}|n"

    def at_say(self, speaker, message, **kwargs):
        """React to someone speaking in the room."""
        if speaker != self:
            self.check_triggers("on_speak", speaker=speaker, message=message)

    def at_character_arrive(self, chara, **kwargs):
        """
        Respond to the arrival of a character
        """
        super().at_character_arrive(chara, **kwargs)
        self.check_triggers("char_enter", chara=chara)
        if "aggressive" in self.attributes.get("react_as", ""):
            delay(0.1, self.enter_combat, chara)

    def at_character_depart(self, chara, destination, **kwargs):
        """
        Respond to the departure of a character
        """
        super().at_character_depart(chara, destination, **kwargs)
        self.check_triggers("char_leave", chara=chara, destination=destination)
        if chara == self.db.following:
            # find an exit that goes the same way
            exits = [
                x
                for x in self.location.contents_get(content_type="exit")
                if x.destination == destination
            ]
            if exits:
                # use the exit
                self.execute_cmd(exits[0].name)

    def at_object_receive(self, obj, source_location, **kwargs):
        super().at_object_receive(obj, source_location, **kwargs)
        self.check_triggers("object_receive", item=obj, giver=source_location)

    def return_appearance(self, looker, *, room=False, **kwargs):
        """Return a description of this NPC.

        Args:
            looker (Object): The object looking at us.
            room (bool, optional): If ``True``, return the short room
                description. Defaults to ``False``.
        """

        if room:
            return f"{self.db.shortdesc or self.key} is here."

        if looker != self:
            self.check_triggers("on_look", looker=looker)

        if self.db.dead:
            return f"{self.key} is lying here, lifeless."

        longdesc = self.db.long_desc or self.db.desc or "You see nothing special."
        status = get_health_description(self)
        return f"{longdesc}\n\n{self.key.capitalize()} {status}"

    def at_damage(self, attacker, damage, damage_type=None, critical=False):
        """
        Apply damage, after taking into account damage resistances.
        """
        dmg = super().at_damage(attacker, damage, damage_type=damage_type, critical=critical)
        self.check_triggers("on_attack", attacker=attacker, damage=dmg)

        if self.traits.health.value <= 0:
            # we've been defeated!
            self.on_death(attacker)
            return dmg

        if "timid" in self.attributes.get("react_as", ""):
            self.at_emote("flees!")
            self.db.fleeing = True
            if combat_script := self.location.scripts.get("combat"):
                combat_script = combat_script[0]
                if not combat_script.remove_combatant(self):
                    return dmg
            # there's a 50/50 chance the object will escape forever
            if randint(0, 1):
                self.move_to(None)
                self.delete()
            else:
                flee_dir = choice(self.location.contents_get(content_type="exit"))
                flee_dir.at_traverse(self, flee_dir.destination)
            return dmg

        threshold = self.attributes.get("flee_at", 25)
        if self.traits.health.value <= threshold:
            self.execute_cmd("flee")

        # change target to the attacker
        if not self.db.combat_target:
            self.enter_combat(attacker)
        else:
            self.db.combat_target = attacker
        return dmg
    def enter_combat(self, target, **kwargs):
        """
        initiate combat against another character
        """
        if weapons := self.wielding:
            weapon = weapons[0]
        else:
            weapon = self

        self.at_emote("$conj(charges) at {target}!", mapping={"target": target})
        location = self.location

        from typeclasses.scripts import get_or_create_combat_script

        combat_script = get_or_create_combat_script(location)

        self.db.combat_target = target
        # adding a combatant to combat just returns True if they're already there, so this is safe
        if not combat_script.add_combatant(self, enemy=target):
            return

        self.attack(target, weapon)

    def at_pre_attack(self, wielder, **kwargs):
        """
        NPCs can use themselves as their weapon data; verify that they can attack
        """
        if self != wielder:
            return
        if not (weapon := self.db.natural_weapon):
            return
        # make sure wielder has enough strength left
        if self.traits.stamina.value < weapon.get("stamina_cost", 5):
            return False
        return True

    def at_attack(self, wielder, target, **kwargs):
        """
        attack with your natural weapon
        """
        if not getattr(target, "traits", None) or not callable(getattr(target, "at_damage", None)):
            if hasattr(wielder, "msg"):
                wielder.msg("You can't attack that.")
            return
        from world.system import stat_manager

        weapon = self.db.natural_weapon
        damage = weapon.get("damage", 0)
        speed = weapon.get("speed", 10)
        # attack with your natural attack skill - whatever that is
        result = self.use_skill(weapon.get("skill"), speed=speed)
        damage = damage * result
        self.traits.stamina.current -= weapon.get("stamina_cost", 5)
        if not stat_manager.check_hit(wielder, target):
            self.at_emote(
                f"$conj(swings) $pron(your) {weapon.get('name')} at $you(target), but $conj(misses).",
                mapping={"target": target},
            )
        else:
            if combat_utils.roll_evade(wielder, target):
                self.at_emote(
                    f"$conj(swings) $pron(your) {weapon.get('name')} at $you(target), but they evade.",
                    mapping={"target": target},
                )
                return
            verb = weapon.get("damage_type", "hits")
            crit = stat_manager.roll_crit(wielder, target)
            if crit:
                damage = stat_manager.crit_damage(wielder, damage)
            wielder.at_emote(
                f"$conj({verb}) $you(target) with $pron(your) {weapon.get('name')}.",
                mapping={"target": target},
            )
            target.at_damage(wielder, damage, weapon.get("damage_type"), critical=crit)
        return

    def at_tick(self):
        super().at_tick()
        self.check_triggers("on_timer")
