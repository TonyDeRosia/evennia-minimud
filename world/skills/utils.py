from combat.round_manager import CombatRoundManager


def maybe_start_combat(attacker, target):
    """Ensure ``attacker`` and ``target`` are in combat together."""
    manager = CombatRoundManager.get()
    inst = manager.get_combatant_combat(attacker)
    if inst:
        if all(target is not c for c in inst.combatants):
            inst.add_combatant(target)
    else:
        inst = manager.get_combatant_combat(target)
        if inst:
            inst.add_combatant(attacker)
        else:
            inst = manager.start_combat([attacker, target])
    if hasattr(attacker, "db"):
        attacker.db.combat_target = target
    if hasattr(target, "db"):
        target.db.combat_target = attacker
    return inst
