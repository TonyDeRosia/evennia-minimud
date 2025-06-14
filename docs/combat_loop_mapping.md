# Combat Loop Mapping

This project models its turn-based fighting system after the traditional combat loops used in **ROM MUD**. The following sections outline how the core components correspond to classic functions like `violence_update` and `multi_hit`.

## CombatRoundManager

File: `combat/round_manager.py`

- Maintains a registry of all active combat instances keyed by a unique combat id.
- Tracks which combat each combatant belongs to for quick lookup.
- Ticks every few seconds to drive all active combats, much like ROM's `violence_update` that iterates over every character currently fighting.
- Each tick triggers the associated `CombatEngine` to process a new round.
- When `COMBAT_DEBUG_TICKS` is `True` in `server/conf/settings.py`, a debug log is emitted each tick.

## CombatInstance

Created by `CombatRoundManager` when a new combat begins.
- Tracks its participants and keeps them synchronized with the `CombatEngine`.
- Replaces the old room-attached scripts used in earlier versions.

## CombatEngine

File: `combat/engine/combat_engine.py`

- Executes the actual round logic: rolling initiative, queueing actions and resolving them in order.
- The `process_round` method performs multiple attacks when haste allows, providing functionality similar to ROM's `multi_hit` routine.
- Handles defeat, regeneration and experience rewards after each round.

## NPC AI

File: `world/npc_handlers/mob_ai.py`

- Contains `process_mob_ai`, which evaluates behaviours for NPCs each tick.
- When an NPC is in combat, it chooses actions through the combat engine, mirroring how ROM's AI hooks into `violence_update` to decide attacks.

Together these components recreate the familiar combat loop of a ROM MUD within Evennia while remaining fully scriptable.

