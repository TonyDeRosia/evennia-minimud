Evennia: The RPG
What is this?
Evennia is a game engine/framework for creating online multiplayer text games, such as MUDs.

This project is a compact, fully-functional RPG-style MUD built using Evennia, with minimal custom code and heavy use of community-contributed packages.

Why?
I wanted to see how feasible it is for a new developer to build and launch a complete game using Evennia. This project serves both as a personal experiment and as a reference for anyone interested in creating their own game.

Evennia is powerful and flexible, but intentionally unopinionated. That makes it great for custom work—but a bit sparse out of the box. The community contribs, however, are plug-and-play systems that can rapidly enhance your game. If they fit your needs, just drop them in.

Can I use this as a base for my own game?
Yes! Please do. Installation instructions are below, and additional documentation can be found on the Evennia website.

Getting Started
This project uses a round-based combat system that processes queued actions each tick. Refer to docs/combat_loop_mapping.md for a full walkthrough of combat.

Currency
There are four coin types:

1 Silver   = 100 Copper
1 Gold     = 10 Silver   = 1,000 Copper
1 Platinum = 10 Gold    = 10,000 Copper
Typical usage:

Copper – meals, basic supplies.

Silver – standard gear and services.

Gold – premium items, mounts, property.

Platinum – rare transactions or guild-level assets.

Use the bank command near a banker:

```bash
bank balance
bank deposit <amount [coin]>
bank withdraw <amount [coin]>
bank transfer <amount [coin]> <player>
```
Minimap
Rooms display a visual minimap:

```
     N
  __^__
 |     |
W<| [X] |>E
 |____|
     v
     S
```
Rooms can optionally store (x, y, "area") coordinates for use with xyzgrid mapping.

Installation
Requirements
Python 3.12+

Git

Windows
```bash
git clone https://github.com/InspectorCaracal/evennia-minimud.git
cd evennia-minimud
py -m venv .venv
.venv\Scripts\activate
pip install .
py -m evennia
evennia migrate
evennia start
```
Linux / macOS
```bash
git clone https://github.com/InspectorCaracal/evennia-minimud.git
cd evennia-minimud
python3 -m venv .venv
source .venv/bin/activate
pip install .
evennia migrate
evennia start
```
Follow the prompt to create your superuser account.

Setup Continued
```bash
evennia xyzgrid init
evennia xyzgrid spawn
evennia reload
```
Then, in-game:
```bash
ic
@initmidgard
```
This populates rooms 200050-200150 so @teleport works.
Creating NPCs
Use:

```bash
cnpc start <key>
```
This launches the builder menu. Choose an NPC type:

merchant, banker, trainer, wanderer, combatant

Combatants use CombatNPC and require a class from world.scripts.classes.

Trigger syntax is flexible:
```json

{
  "on_enter": [
    {"match": "", "responses": ["say Hello", "emote waves"]}
  ]
}
```
You can also run mob commands such as:
```bash

mob mpdamage <target> <amount> [type]

mob mpapply <target> <effect> [duration]

mob mpcall <module.func>
```

To respawn, clone, or list:

```bash
@spawnnpc <proto>
@clonenpc <existing> [= new_name]
@deletenpc <npc>
@listnpcs [area]
```
To assign AI:

passive, aggressive, defensive, wander, scripted

Mob Builder & MEdit
Use mobbuilder or quickmob:

```bash
@quickmob goblin warrior
```
Use medit <vnum> to edit a numeric prototype or:

```bash
medit create <vnum>
Set stats, then save as a prototype. Mobs saved with mobbuilder use the prefix mob_.

```
Mob Prototype Manager
```bash
@mobproto create 1 goblin
@mobproto set 1 level 3
@mobproto spawn 1
```
Use `@listvnums <npc|room|object> [area]` to see free numbers.
Spawning and Room Systems
Room JSONs may include:
```json

"spawns": [
  {"proto": "mob_goblin", "max_spawns": 2, "spawn_interval": 300}
]
```
See `docs/mob_respawn.md` for a full overview of how these entries are stored
and managed at runtime.
MobRespawnManager automatically registers spawns when a room prototype is saved.
The `spawn_interval` value is stored internally on MobRespawnManager entries as
`respawn_rate`. Commands like `@showspawns` display this runtime field. If
spawns appear to be missing (for example after a server restart), use:

```bash
@spawnreload
@forcerespawn <vnum>
@showspawns [vnum]
```
Troubleshooting Mob Spawns
If NPCs do not appear as expected, inspect `scripts/spawn_manager.py` to ensure
the global spawn manager is running. Use `@spawnreload` to reload spawn entries
from room prototypes and `@showspawns <room_vnum>` to list registered spawns.
Check server logs for messages from `MobRespawnManager` about errors or skipped
rooms. Also confirm each room prototype includes a valid `spawns` field with the
correct NPC identifiers.
The `redit` spawn editor now warns if you try to add an unknown prototype.
It will also alert you when a numeric prototype exists only in memory:
`Prototype <vnum> is not saved to disk. Use 'Save & write prototype' to persist it.`
Weapon Creation
```bash
cweapon "longsword" mainhand 1d8 4 STR+2 A reliable longsword.
inspect longsword-1
```
Supports flat or dice damage (e.g. 2d6). Add /unidentified to hide stats.

Combat System
Modular combat using a 2-second tick:

```python
from combat.round_manager import CombatRoundManager
CombatRoundManager.get().start_combat([fighter1, fighter2])
```
The old `combat.combat_manager` module now simply re-exports these
classes and is considered deprecated.

The primary combat classes `CombatRoundManager` and `CombatInstance` live in
`combat/round_manager.py`. Player characters start fights using the `CmdAttack`
command defined in `commands/combat.py`.

Supports action queues, status effects, resistances

Fully pluggable and extendable—combat emits Django signals and you can
override the `DamageProcessor`, `IDeathHandler` or NPC AI routines. See
`docs/combat_loop_mapping.md` for examples. For a hands-on demonstration, see
`docs/quickstart_combat.md`.

The available spells and the ``Spell`` dataclass now live in ``combat.spells``.

`combat.scripts` exposes helper functions like `queue_spell` and
`queue_skill` for casting and using abilities. They automatically
queue a `SpellAction` or `SkillAction` on the active combat engine or
resolve the effect immediately when outside of combat.

Running Tests
Before running `pytest`, you **must** install the testing requirements so Django
and Evennia are available. Use the helper script:

```bash
scripts/setup_test_env.sh
```

which installs Django, Evennia and the rest of the test dependencies. You can
also install them manually:

```bash
pip install -r requirements-test.txt
pip install -e .
```

Skipping this step will cause `pytest` to fail during collection with missing
Django or Evennia modules. After the environment is prepared, run:

```bash
pytest -q
```

Area JSON Format
Room VNUMs now tracked in world/prototypes/areas/*.json under a rooms list. See docs/area_json.md for format details.

