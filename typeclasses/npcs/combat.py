"""Combat-ready NPC typeclass."""

from . import BaseNPC


class CombatNPC(BaseNPC):
    """NPC that can engage in combat by default."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.can_attack = True

    def at_combat_turn(self, target):
        """Hook called each combat round by the combat engine."""
        if not getattr(self.db, "auto_attack_enabled", False):
            return
        if not target:
            return
        engine = getattr(getattr(self, "ndb", None), "combat_engine", None)
        if engine:
            from combat.combat_actions import AttackAction

            engine.queue_action(self, AttackAction(self, target))

