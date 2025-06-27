# Mob Respawn System

This project uses a lightweight respawn manager to populate rooms with NPCs. Spawn data lives on each room object under `room.db.spawn_entries` and is updated automatically as mobs die and respawn.

## spawn_entries Structure

`room.db.spawn_entries` is a list where each element tracks one NPC prototype. Fields include:

- `area` – lowercase area name
- `prototype` – numeric VNUM or string key identifying the NPC prototype
- `room_id` – VNUM of the room
- `max_count` – maximum number of active mobs allowed
- `respawn_rate` – seconds before a dead mob can respawn (derived from `spawn_interval` in room prototypes)
- `active_mobs` – list of object ids currently alive in the room
- `dead_mobs` – list of dictionaries containing `id` and `time_of_death`
- `last_spawn` – timestamp of the most recent spawn

## MobRespawnManager and MobRespawnTracker

`MobRespawnManager` is a global script that ticks every minute. For each area it maintains a `MobRespawnTracker` which knows all rooms in that area with spawn data. Trackers monitor deaths and spawns, update `spawn_entries`, and spawn new mobs when the respawn timer has elapsed.

Rooms register their spawn information through `register_room_spawn` when a room prototype is saved. The manager exposes `record_spawn`, `record_death` and `force_respawn` helpers for other systems.

## Configuring Spawns with redit

Builders edit room prototypes using `redit <vnum>`. Choose **Edit spawns** to open the spawn editor. Commands inside the editor:

```
add <proto> <max> <rate>  – add or update a spawn entry
remove <proto>            – delete a spawn entry
done                      – return to the main menu
```

`<proto>` is either a numeric VNUM from the mob database or the key of a registry prototype. `<rate>` is the spawn interval in seconds. Saving the room prototype automatically registers the spawns with `MobRespawnManager` and forces a respawn.

## Useful Commands

Several commands interact with the respawn system:

- `@spawnreload` – reload spawn entries from all room prototypes
- `@forcerespawn <room_vnum>` – immediately run spawn checks for a room
- `areas.reset <area>` – repopulate an entire area
- `@showspawns [room_vnum]` – list current spawn data

See `commands/admin/spawncontrol.py` for implementation details.
