"""Regenerate character resources using the global tick.

This script no longer schedules its own interval but instead reacts to
``GlobalTickScript`` firing the global tick signal.
"""

from evennia.scripts.scripts import DefaultScript
from typeclasses.global_tick import TICK
from typeclasses.characters import Character, NPC


class GlobalHealingScript(DefaultScript):
    """Apply passive regeneration to all characters once per global tick."""

    def at_script_creation(self):
        """Configure script to persist without its own interval."""
        self.interval = 0
        self.persistent = True

    def at_start(self):
        """Connect to the global tick signal."""
        TICK.connect(self.on_tick)

    def at_stop(self):
        """Disconnect from the global tick signal."""
        TICK.disconnect(self.on_tick)

    def on_tick(self, sender=None, **kwargs):
        """Heal all characters when the global tick fires."""
        targets = list(Character.objects.all()) + list(NPC.objects.all())
        seen = set()
        for obj in targets:
            if obj in seen:
                continue
            seen.add(obj)
            if obj.tags.has("unconscious", category="status"):
                continue
            derived = obj.db.derived_stats or {}
            healed = False
            for key in ("health", "mana", "stamina"):
                trait = obj.traits.get(key)
                if not trait:
                    continue
                regen = int(derived.get(f"{key}_regen", 0))
                if regen <= 0 or trait.current >= trait.max:
                    continue
                trait.current = min(trait.current + regen, trait.max)
                healed = True
            if healed and obj.sessions.count():
                obj.msg("You have recovered some.", prompt=obj.get_resource_prompt())

    def at_repeat(self):
        """Unused; regeneration is handled via :func:`on_tick`."""
        pass

