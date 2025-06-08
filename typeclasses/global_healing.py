"""Regenerate character resources on a global interval."""

from evennia.scripts.scripts import DefaultScript
from typeclasses.characters import Character, NPC


class GlobalHealingScript(DefaultScript):
    """Apply passive regeneration to all characters periodically."""

    def at_script_creation(self):
        """Set up the repeating script."""
        self.interval = 60
        self.persistent = True

    def at_repeat(self):
        """Heal all characters once per interval."""
        targets = list(Character.objects.all()) + list(NPC.objects.all())
        seen = set()
        for obj in targets:
            if obj in seen:
                continue
            seen.add(obj)
            if obj.tags.has("unconscious", category="status"):
                continue
            derived = obj.db.derived_stats or {}
            for key in ("health", "mana", "stamina"):
                trait = obj.traits.get(key)
                if not trait:
                    continue
                regen = int(derived.get(f"{key}_regen", 0))
                if regen <= 0 or trait.current >= trait.max:
                    continue
                trait.current = min(trait.current + regen, trait.max)
            if obj.sessions.count():
                obj.refresh_prompt()

