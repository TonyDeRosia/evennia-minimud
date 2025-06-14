def _gather_actions(self) -> list[tuple[int, int, int, CombatParticipant, Action]]:
    """Collect and sort all actions for this round."""
    actions: list[tuple[int, int, int, CombatParticipant, Action]] = []
    for participant in list(self.queue):
        actor = participant.actor
        hp = _current_hp(actor)
        if hp <= 0:
            continue
        target = getattr(getattr(actor, "db", None), "combat_target", None)
        hook = getattr(actor, "at_combat_turn", None)
        if callable(hook):
            hook(target)

        if participant.next_action:
            queued = list(participant.next_action)
        elif target:
            queued = [AttackAction(actor, target)]
        else:
            # fallback: attack any valid enemy in the room
            enemies = [
                p.actor
                for p in self.participants
                if p.actor is not actor and _current_hp(p.actor) > 0
            ]
            if enemies:
                queued = [AttackAction(actor, enemies[0])]
            else:
                queued = []
                if hasattr(actor, "msg"):
                    actor.msg("You hesitate, unsure of what to do.")

        # add extra attacks based on haste
        haste = state_manager.get_effective_stat(actor, "haste")
        extra = max(0, haste // HASTE_PER_EXTRA_ATTACK)
        # limit total attacks to prevent runaway bursts
        extra = min(extra, MAX_ATTACKS_PER_ROUND - 1)
        if extra and queued:
            extras: list[Action] = []
            for action in queued:
                if isinstance(action, AttackAction):
                    for _ in range(extra):
                        extras.append(AttackAction(actor, action.target))
            queued.extend(extras)

        for idx, action in enumerate(queued):
            actions.append(
                (
                    participant.initiative,
                    getattr(action, "priority", 0),
                    -idx,
                    participant,
                    action,
                )
            )

    actions.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
    return actions

def _execute_action(
    self, participant: CombatParticipant, action: Action, damage_totals: Dict[object, int]
) -> None:
    """Validate and resolve ``action`` for ``participant``."""
    actor = participant.actor
    valid, err = action.validate()
    if not valid:
        if hasattr(actor, "msg") and err:
            actor.msg(err)
        if action in participant.next_action:
            participant.next_action.remove(action)
        return

    result = action.resolve()

    if action in participant.next_action:
        participant.next_action.remove(action)

    damage_done = 0
    if result.damage and result.target:
        dt = result.damage_type
        if isinstance(dt, str):
            try:
                dt = DamageType(dt)
            except ValueError:
                dt = None
        damage_done = self.apply_damage(actor, result.target, result.damage, dt)
        if not result.message:
            self.dam_message(actor, result.target, damage_done)
        damage_totals[actor] = damage_totals.get(actor, 0) + damage_done

    if result.target:
        cond = get_health_description(result.target)
        self.round_output.append(f"The {result.target.key} {cond}")

    if actor.location and result.message:
        actor.location.msg_contents(result.message)
    
    # Only track aggro and handle defeat if we have a valid target
    if result.target:
        self.track_aggro(result.target, actor)
        target_hp = _current_hp(result.target)
        if target_hp <= 0:
            self.handle_defeat(result.target, actor)

def _summarize_damage(self, damage_totals: Dict[object, int]) -> None:
    """Append a short damage summary to the round output."""
    summary_lines = [
        f"{getattr(att, 'key', att)} dealt {dmg} damage."
        for att, dmg in damage_totals.items()
        if dmg > 0  # Only show non-zero damage
    ]
    if summary_lines:
        self.round_output.extend(summary_lines)

def _broadcast_round_output(self) -> None:
    """Send accumulated round output to the appropriate location."""
    if not self.round_output:
        return
    msg = "\n".join(self.round_output)
    room = None
    if self.participants:
        room = getattr(self.participants[0].actor, "location", None)
    if room:
        room.msg_contents(msg)
    else:
        for participant in self.participants:
            actor = participant.actor
            if hasattr(actor, "msg"):
                actor.msg(msg)

def process_round(self) -> None:
    """Execute all queued actions for the current round.

    Side Effects
    ------------
    Applies damage, sends combat messages, awards experience and
    schedules the next round using :func:`evennia.utils.delay`.
    """
    self.start_round()
    self.round_output = []
    damage_totals: Dict[object, int] = {}

    actions = self._gather_actions()
    for _, _, _, participant, action in actions:
        self._execute_action(participant, action, damage_totals)

    self.cleanup_environment()
    self._summarize_damage(damage_totals)
    self._broadcast_round_output()

    self.round += 1
    if self.round_time is not None and any(_current_hp(p.actor) > 0 for p in self.participants):
        delay(self.round_time, self.process_round)