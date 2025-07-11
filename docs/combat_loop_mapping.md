# Combat Loop Mapping

This project models its turn-based fighting system after the traditional combat loops used in **ROM MUD**. The following sections outline how the core components correspond to classic functions like `violence_update` and `multi_hit`.

## CombatRoundManager

File: `combat/round_manager.py`

- The old `combat.combat_manager` module now simply re-exports these classes for compatibility.

- Maintains a registry of all active combat instances keyed by a unique combat id.
- Tracks which combat each combatant belongs to for quick lookup.
- Each `CombatInstance` schedules a tick every few seconds, much like ROM's
  `violence_update` that iterates over every character currently fighting.
- Each tick triggers the associated `CombatEngine` to process a new round.
- The `round_time` argument used when creating a combat sets this tick interval
  and is forwarded to `CombatEngine` so its automatic round timer matches.
- When `COMBAT_DEBUG_TICKS` is `True` in `server/conf/settings.py`, a debug log is emitted each tick.

## CombatInstance

File: `combat/round_manager.py`

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
from combat.round_manager import CombatRoundManager
from combat.combat_actions import AttackAction

# attacker and target are Character objects already in the same room
CombatRoundManager.get().start_combat([attacker, target])

engine = attacker.ndb.combat_engine
engine.queue_action(attacker, AttackAction(attacker, target))

# The round manager will call `process_round` automatically every tick
# which resolves queued actions and broadcasts the results to the room.
```
In-game, players typically use the `attack` command (`CmdAttack` in
`commands/combat.py`) which queues an appropriate `AttackAction` for them.

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

## Additional Mechanics

- **Parry and Dodge** – `CombatMath.check_hit` mirrors ROM's `check_dodge` and
  `check_parry` functions. After verifying a hit, it rolls
  `roll_evade`, `roll_parry` and `roll_block` to allow the defender a chance to
  avoid damage based on their `evasion`, `parry_rate` and `block_rate` stats.

- **Wimpy Fleeing** – NPCs with the `wimpy` flag run away when their HP drops
  below a threshold. The `_check_wimpy` helper in `world/npc_handlers/mob_ai.py`
  compares the mob's current HP against `flee_at` (defaulting to 25% of maximum)
  and issues the `flee` command when triggered.
- **Dead NPC Cleanup** – combatants flagged with `db.is_dead` skip any queued
  actions and are removed from combat at the end of the round.
- **Experience Rewards** – when an `AttackAction` drops a combatant to 0 HP,
  `CombatRoundManager` handles their defeat. The target's `on_death` hook runs
  and any accumulated XP is distributed to contributors.

## Combat Signals

Several Django signals are emitted during the combat lifecycle. External
modules can subscribe to these to trigger custom behaviour.

- `combat.events.combat_started` - sent when `CombatRoundManager.start_combat`
  begins a new combat instance.
- `combat.events.round_processed` - fired at the end of every round from
  `CombatInstance.process_round`.
- `combat.events.combatant_defeated` - emitted by `DamageProcessor.handle_defeat`
  when a fighter is taken out.
- `combat.events.combat_ended` - sent after cleanup in
  `CombatInstance.end_combat`.

Listeners can connect using Django's `receiver` decorator or the `connect` method:

```python
from combat.events import combatant_defeated
from django.dispatch import receiver

@receiver(combatant_defeated)
def on_defeat(sender, target, attacker, **kwargs):
    print(f"{target} was defeated by {attacker}!")
```

## Extending the Combat System

The combat package provides several hooks for customizing behaviour.

### Overriding `DamageProcessor`

Subclass `DamageProcessor` to alter how actions resolve or messages are sent:

```python
from combat.damage_processor import DamageProcessor

class LoggingProcessor(DamageProcessor):
    def dam_message(self, attacker, target, damage, **kwargs):
        super().dam_message(attacker, target, damage, **kwargs)
        print(f"[LOG] {attacker} hit {target} for {damage}")
```

Assign your processor when creating a combat engine:

```python
from combat.engine import CombatEngine

engine = CombatEngine(fighters)
engine.processor = LoggingProcessor(engine, engine.turn_manager, engine.aggro_tracker)
```

### Custom Death Handlers

Implement `IDeathHandler` and register it with `set_handler` to change what happens when a combatant dies:

```python
from world.mechanics.death_handlers import IDeathHandler, set_handler

class SimpleGrimReaper(IDeathHandler):
    def handle(self, victim, killer=None):
        victim.location.msg_contents(f"{victim.key} is claimed by the reaper!")
        return None

set_handler(SimpleGrimReaper())
```

### Replacing NPC AI

`world.npc_handlers.mob_ai.process_mob_ai` controls standard NPC behaviour. You can wrap or replace it:

```python
from world.npc_handlers import mob_ai

def berserk_ai(npc):
    if npc.db.berserk:
        npc.execute_cmd("bash")
        return
    mob_ai.process_mob_ai(npc)
```

Run your function from the `GlobalNPCAI` script or another scheduler. Combined with the combat signals above, these hooks let you deeply customize the flow of battle.
