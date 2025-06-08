from random import randint, choice
from string import punctuation
from evennia import AttributeProperty
from evennia.utils import lazy_property, iter_to_str, delay, logger, make_iter
import importlib
from evennia.contrib.rpg.traits import TraitHandler
from evennia.contrib.game_systems.clothing.clothing import (
    ClothedCharacter,
    get_worn_clothes,
)
from evennia.contrib.game_systems.cooldowns import CooldownHandler
from evennia.prototypes.spawner import spawn
from utils.currency import to_copper, from_copper
from utils import normalize_slot
from utils.slots import SLOT_ORDER
from collections.abc import Mapping
import math

from .objects import ObjectParent

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


        self.db.guild = ""
        self.db.guild_points = {}
        self.db.guild_rank = ""
        self.db.stat_overrides = {}
        self.db.equip_bonuses = {}
        self.db.sated = 5
        from typeclasses.global_tick import register_character
        register_character(self)

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

    def at_object_delete(self):
        from typeclasses.global_tick import unregister_character
        unregister_character(self)
        return super().at_object_delete()
        
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
            self.traits.stamina.current = max(
                self.traits.stamina.current - cost, 0
            )

        # check if we have auto-prompt in settings
        if self.account and (settings := self.account.db.settings):
            if settings.get("auto prompt"):
                status = self.get_display_status(self)
                self.msg(prompt=status)

    def at_damage(self, attacker, damage, damage_type=None):
        """
        Apply damage, after taking into account damage resistances.
        """
        # apply armor damage reduction
        damage -= self.defense(damage_type)
        damage = max(0, damage)
        self.traits.health.current -= damage
        self.msg(f"You take {damage} damage from {attacker.get_display_name(self)}.")
        attacker.msg(f"You deal {damage} damage to {self.get_display_name(attacker)}.")
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
            if (bounty := self.db.bounty):
                wallet = attacker.db.coins or {}
                total = to_copper(wallet) + bounty
                attacker.db.coins = from_copper(total)
                attacker.msg(f"You claim {bounty} coins for defeating {self.key}.")
                self.db.bounty = 0

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
            if any(obj.tags.has("shield", category="flag") for obj in get_worn_clothes(self)):
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
        weapon.db.equipped_by = self
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
        weapon.db.equipped_by = None
        self.update_carry_weight()
        from world.system import stat_manager
        stat_manager.remove_item_bonuses(self, weapon)
        # return the list of hands that are no longer holding the weapon
        return freed

    def use_skill(self, skill_name, *args, **kwargs):
        """
        Attempt to use a skill, applying any stat bonus as necessary.
        """
        # handle cases where this was called but there's no skill being used
        if not skill_name:
            return 1
        # if we don't have the skill, we can't use it
        if not (skill_trait := self.traits.get(skill_name)):
            return 0
        from world.system import state_manager

        # check if this skill has a related base stat
        stat_bonus = 0
        if stat := getattr(skill_trait, "stat", None):
            stat_bonus = state_manager.get_effective_stat(self, stat)
        # finally, return the skill plus stat
        return skill_trait.value + stat_bonus

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
        chunks.append(
            f"Health {hp}% : Mana {mp}% : Stamina {sp}%"
        )

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
        pass

    def at_character_depart(self, chara, destination, **kwargs):
        """
        Respond to the departure of a character
        """
        pass

    def at_tick(self):
        """Handle one tick of regeneration.

        The global ticker calls this once every minute. Any passive healing or
        status effects are advanced here.

        Returns:
            bool: ``True`` if any resources were changed.
        """
        from world.system import state_manager

        # advance effect and status timers
        state_manager.tick_character(self)

        # apply passive regeneration and report if anything changed
        healed = state_manager.apply_regen(self)

        return bool(healed)

    def refresh_prompt(self):
        """Refresh the player's prompt display."""
        if self.sessions.count():
            self.msg(prompt=self.get_resource_prompt())

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


    def at_damage(self, attacker, damage, damage_type=None):
        super().at_damage(attacker, damage, damage_type=damage_type)
        if self.traits.health.value < 50:
            status = self.get_display_status(self)
            self.msg(prompt=status)

    def attack(self, target, weapon, **kwargs):
        """
        Execute an attack

        Args:
            target (Object or None): the entity being attacked. if None, attempts to use the combat_target db attribute
            weapon (Object): the object dealing damage
        """
        # can't attack if we're not in combat!
        if not self.in_combat:
            return
        # can't attack if we're fleeing!
        if self.db.fleeing:
            return
        # make sure that we can use our chosen weapon
        if not (hasattr(weapon, "at_pre_attack") and hasattr(weapon, "at_attack")):
            self.msg(f"You cannot attack with {weapon.get_numbered_name(1, self)}.")
            return
        if not weapon.at_pre_attack(self):
            # the method handles its own error messaging
            return

        # if target is not set, use stored target
        if not target:
            # make sure there's a stored target
            if not (target := self.db.combat_target):
                self.msg("You cannot attack nothing.")
                return

        if target.location != self.location:
            self.msg("You don't see your target.")
            return

        # attack with the weapon
        weapon.at_attack(self, target)

        status = self.get_display_status(self)
        self.msg(prompt=status)

        # check if we have auto-attack in settings
        if self.account and (settings := self.account.db.settings):
            if settings.get("auto attack") and (speed := weapon.speed):
                # queue up next attack; use None for target to reference stored target on execution
                delay(speed + 1, self.attack, None, weapon, persistent=True)

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


class NPC(Character):
    """
    The base typeclass for non-player characters, implementing behavioral AI.

    NPCs can be assigned roles with ``obj.tags.add("<role>", category="npc_role")``.
    """

    # defines what color this NPC's name will display in
    name_color = AttributeProperty("w")
    # mapping of event triggers -> reactions
    triggers = AttributeProperty([])

    def at_object_creation(self):
        super().at_object_creation()
        if self.db.triggers is None:
            self.db.triggers = []

    def check_triggers(self, event, **kwargs):
        """Evaluate stored triggers for a given event."""
        triggers = self.db.triggers or []

        if isinstance(triggers, dict):
            newlist = []
            for evt, data in triggers.items():
                if isinstance(data, tuple):
                    match, reacts = data
                    reacts = [reacts]
                elif isinstance(data, dict):
                    match = data.get("match")
                    reacts = data.get("reactions") or data.get("reaction") or []
                else:
                    continue
                for react in make_iter(reacts):
                    newlist.append({"event": evt, "match": match, "action": react})
            self.db.triggers = triggers = newlist

        for trig in make_iter(triggers):
            if not isinstance(trig, dict):
                continue
            if trig.get("event") != event:
                continue
            match = trig.get("match")
            if match:
                text = str(kwargs.get("message") or kwargs.get("text") or "")
                if isinstance(match, (list, tuple)):
                    if not any(m.lower() in text.lower() for m in match):
                        continue
                elif str(match).lower() not in text.lower():
                    continue
            actions = trig.get("action") or trig.get("actions")
            for react in make_iter(actions):
                if isinstance(react, str):
                    if " " in react:
                        action, arg = react.split(" ", 1)
                    else:
                        action, arg = react, ""
                elif isinstance(react, dict) and len(react) == 1:
                    action, arg = next(iter(react.items()))
                else:
                    continue
                self._execute_reaction(action.lower(), arg, **kwargs)

    def _execute_reaction(self, action, arg, **kwargs):
        """Execute a single reaction action."""
        try:
            if action == "say":
                self.execute_cmd(f"say {arg}")
            elif action in ("emote", "pose"):
                self.execute_cmd(f"{action} {arg}")
            elif action == "move":
                if arg:
                    self.execute_cmd(arg)
            elif action == "attack":
                target = arg or kwargs.get("target")
                if isinstance(target, str):
                    target = self.search(target)
                if target:
                    if not self.in_combat:
                        self.enter_combat(target)
                    else:
                        weapon = self.wielding[0] if self.wielding else self
                        self.attack(target, weapon)
            elif action == "script":
                module, func = arg.rsplit(".", 1)
                mod = importlib.import_module(module)
                getattr(mod, func)(self, **kwargs)
            else:
                self.execute_cmd(f"{action} {arg}" if arg else action)
        except Exception as err:  # pragma: no cover - log errors
            logger.log_err(f"NPC trigger error on {self}: {err}")

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
        if "aggressive" in self.attributes.get("react_as", ""):
            delay(0.1, self.enter_combat, chara)
        self.check_triggers("on_enter", chara=chara)

    def at_character_depart(self, chara, destination, **kwargs):
        """
        Respond to the departure of a character
        """
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
        self.check_triggers("on_give_item", item=obj, giver=source_location)

    def return_appearance(self, looker, **kwargs):
        text = super().return_appearance(looker, **kwargs)
        if looker != self:
            self.check_triggers("on_look", looker=looker)
        return text

    def at_damage(self, attacker, damage, damage_type=None):
        """
        Apply damage, after taking into account damage resistances.
        """
        super().at_damage(attacker, damage, damage_type=damage_type)
        self.check_triggers("on_attack", attacker=attacker, damage=damage)

        if self.traits.health.value <= 0:
            # we've been defeated!
            # create loot drops
            objs = spawn(*list(self.db.drops))
            for obj in objs:
                obj.location = self.location
            # delete ourself
            self.delete()
            return

        if "timid" in self.attributes.get("react_as", ""):
            self.at_emote("flees!")
            self.db.fleeing = True
            if combat_script := self.location.scripts.get("combat"):
                combat_script = combat_script[0]
                if not combat_script.remove_combatant(self):
                    return
            # there's a 50/50 chance the object will escape forever
            if randint(0, 1):
                self.move_to(None)
                self.delete()
            else:
                flee_dir = choice(self.location.contents_get(content_type="exit"))
                flee_dir.at_traverse(self, flee_dir.destination)
            return

        threshold = self.attributes.get("flee_at", 25)
        if self.traits.health.value <= threshold:
            self.execute_cmd("flee")

        # change target to the attacker
        if not self.db.combat_target:
            self.enter_combat(attacker)
        else:
            self.db.combat_target = attacker

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

        if not (combat_script := location.scripts.get("combat")):
            # there's no combat instance; start one
            from typeclasses.scripts import CombatScript

            location.scripts.add(CombatScript, key="combat")
            combat_script = location.scripts.get("combat")
        combat_script = combat_script[0]

        self.db.combat_target = target
        # adding a combatant to combat just returns True if they're already there, so this is safe
        if not combat_script.add_combatant(self, enemy=target):
            return

        self.attack(target, weapon)

    def attack(self, target, weapon, **kwargs):
        # can't attack if we're not in combat, or if we're fleeing
        if not self.in_combat or self.db.fleeing or self.tags.has("unconscious"):
            return

        # if target is not set, use stored target
        if not target:
            # make sure there's a stored target
            if not (target := self.db.combat_target):
                return
        # verify that target is still here
        if self.location != target.location:
            return

        # make sure that we can use our chosen weapon
        if not (hasattr(weapon, "at_pre_attack") and hasattr(weapon, "at_attack")):
            return
        if not weapon.at_pre_attack(self):
            return

        # attack with the weapon
        weapon.at_attack(self, target)
        # queue up next attack; use None for target to reference stored target on execution
        delay(weapon.speed + 1, self.attack, None, weapon, persistent=True)
        self.check_triggers("on_attack", target=target, weapon=weapon)

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
        # can't attack if on cooldown
        if not wielder.cooldowns.ready("attack"):
            return False

        return True

    def at_attack(self, wielder, target, **kwargs):
        """
        attack with your natural weapon
        """
        weapon = self.db.natural_weapon
        damage = weapon.get("damage", 0)
        speed = weapon.get("speed", 10)
        # attack with your natural attack skill - whatever that is
        result = self.use_skill(weapon.get("skill"), speed=speed)
        # apply the weapon damage as a modifier to skill
        damage = damage * result
        # subtract the stamina required to use this
        self.traits.stamina.current -= weapon.get("stamina_cost", 5)
        if not damage:
            # the attack failed
            self.at_emote(
                f"$conj(swings) $pron(your) {weapon.get('name')} at $you(target), but $conj(misses).",
                mapping={"target": target},
            )
        else:
            verb = weapon.get("damage_type", "hits")
            wielder.at_emote(
                f"$conj({verb}) $you(target) with $pron(your) {weapon.get('name')}.",
                mapping={"target": target},
            )
            # the attack succeeded! apply the damage
            target.at_damage(wielder, damage, weapon.get("damage_type"))
        wielder.msg(f"[ Cooldown: {speed} seconds ]")
        wielder.cooldowns.add("attack", speed)

    def at_tick(self):
        """Propagate tick handling and evaluate triggers."""
        changed = super().at_tick()
        self.check_triggers("on_timer")
        return changed
