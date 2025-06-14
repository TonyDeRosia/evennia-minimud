# Combat Loop Mapping

This project models its turn-based fighting system after the traditional combat loops used in **ROM MUD**. The following sections outline how the core components correspond to classic functions like `violence_update` and `multi_hit`.

## CombatRoundManager

File: `combat/round_manager.py`

- Maintains a registry of all active `CombatScript` instances.
- Ticks every few seconds to drive combat across rooms, much like ROM's `violence_update` that iterates over every character currently fighting.
- Each tick triggers the associated `CombatEngine` to process a new round.

## CombatScript

File: `typeclasses/scripts.py`

- Attached to a room when combat begins and keeps track of the two opposing teams of fighters.
- Starts or stops the room's `CombatEngine` and exposes helper methods for adding and removing combatants.
- Serves the role of ROM's per-room fight list, organizing combatants so that `CombatRoundManager` can handle them as a group.

## CombatEngine

File: `combat/combat_engine.py`

- Executes the actual round logic: rolling initiative, queueing actions and resolving them in order.
- The `process_round` method performs multiple attacks when haste allows, providing functionality similar to ROM's `multi_hit` routine.
- Handles defeat, regeneration and experience rewards after each round.

## NPC AI

File: `world/npc_handlers/mob_ai.py`

- Contains `process_mob_ai`, which evaluates behaviours for NPCs each tick.
- When an NPC is in combat, it chooses actions through the combat engine, mirroring how ROM's AI hooks into `violence_update` to decide attacks.

Together these components recreate the familiar combat loop of a ROM MUD within Evennia while remaining fully scriptable.

