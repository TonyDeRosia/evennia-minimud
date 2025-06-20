# Combat Loop Mapping

This project models its turn-based fighting system after the traditional combat loops used in **ROM MUD**. The following sections outline how the core components correspond to classic functions like `violence_update` and `multi_hit`.

## CombatRoundManager

File: `combat/combat_manager.py`

- The old `combat.round_manager` module has been deprecated and now
  simply re-exports these classes for compatibility.

- Maintains a registry of all active combat instances keyed by a unique combat id.
- Tracks which combat each combatant belongs to for quick lookup.
- Each `CombatInstance` schedules a tick every few seconds, much like ROM's
  `violence_update` that iterates over every character currently fighting.
- Each tick triggers the associated `CombatEngine` to process a new round.
- The `round_time` argument used when creating a combat sets this tick interval
  and is forwarded to `CombatEngine` so its automatic round timer matches.
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

## Round Sequence

The following outlines how a single combat round flows through the system:

1. `CombatInstance._tick` calls `process_round` for its own encounter.
2. `CombatInstance.process_round` synchronizes its participants and verifies at least two are still able to fight.
3. If combat continues, it invokes `CombatEngine.process_round` which delegates to the `DamageProcessor`.
4. `DamageProcessor.process_round` starts the round, gathers queued actions from the `TurnManager` and resolves them in initiative order.
5. Defeated combatants are removed and experience rewards granted as part of the processing.
6. After returning, `CombatInstance.sync_participants` runs again to clean up and determine if the combat should end.


## Example: Starting Combat

The following snippet demonstrates a minimal fight between two characters. First create a combat and then queue actions for the round:

```python
from combat.combat_manager import CombatRoundManager
from combat.combat_actions import AttackAction

# attacker and target are Character objects already in the same room
CombatRoundManager.get().start_combat([attacker, target])

engine = attacker.ndb.combat_engine
engine.queue_action(attacker, AttackAction(attacker, target))

# The round manager will call `process_round` automatically every tick
# which resolves queued actions and broadcasts the results to the room.
```

When the round executes you will see messages such as
``Attacker hits Target for 5 damage!`` and the combatants' HP updated.

## Engine Class Reference

```python
from combat.engine import CombatEngine, TurnManager, AggroTracker, DamageProcessor, CombatMath, CombatParticipant
```

- **CombatEngine** – orchestrates rounds and exposes helpers:
  ```python
  engine = CombatEngine(participants)
  ```
- **TurnManager** – builds the queue each round:
  ```python
  manager = TurnManager(engine, participants)
  ```
- **AggroTracker** – records hostility and awards XP:
  ```python
  aggro = AggroTracker()
  aggro.track(target, attacker)
  ```
- **DamageProcessor** – resolves actions and applies damage:
  ```python
  processor = DamageProcessor(engine, manager, aggro)
  processor.apply_damage(attacker, target, 5, None)
  ```
- **CombatMath** – helpers for hit and damage calculations:
  ```python
  hit, _ = CombatMath.check_hit(attacker, target)
  ```
- **CombatParticipant** – dataclass representing a fighter:
  ```python
  participant = CombatParticipant(actor)
  ```

