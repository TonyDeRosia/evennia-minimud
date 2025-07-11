from combat.round_manager import CombatRoundManager


def maybe_start_combat(attacker, target):
    """Ensure ``attacker`` and ``target`` are in combat together."""
    manager = CombatRoundManager.get()
    inst = manager.get_combatant_combat(attacker)
    new_instance = False
    if inst:
        if target not in inst.combatants:
            inst.add_combatant(target)
    else:
        inst = manager.get_combatant_combat(target)
        if inst:
            inst.add_combatant(attacker)
        else:
            inst = manager.start_combat([attacker, target])
            new_instance = True
    if hasattr(attacker, "db"):
        attacker.db.combat_target = target
    if hasattr(target, "db"):
        target.db.combat_target = attacker

    if new_instance and inst.round_number == 0:
        inst.cancel_tick()
        inst.process_round()

    return inst
