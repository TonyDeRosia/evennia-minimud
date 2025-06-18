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
This project uses a round-based combat system that processes queued actions each tick. Refer to docs/combat_loop_mapping.md for a full walkthrough of combat. A summary of default combat abilities can be found in docs/combat_skills.md.

Currency
There are four coin types:

1 Silver   = 100 Copper
1 Gold     = 10 Silver   = 1,000 Copper
1 Platinum = 100 Gold    = 100,000 Copper
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
Python 3.10+

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
Spawning and Room Systems
Room JSONs may include:
```json

"spawns": [
  {"proto": "mob_goblin", "max_spawns": 2, "spawn_interval": 300}
]
SpawnManager automatically registers spawns when a room prototype is saved.
Spawns are not automatically repopulated when the server starts. Use the
commands below to load spawn data or force a respawn if NPCs are missing:

```bash
@spawnreload
@forcerespawn <vnum>
@showspawns [vnum]
```
Weapon Creation
```bash
cweapon "longsword" mainhand 1d8 4 STR+2 A reliable longsword.
inspect longsword-1
```
Supports flat or dice damage (e.g. 2d6). Add /unidentified to hide stats.

Combat System
Modular combat using a 2-second tick:

```python
CombatRoundManager.get().start_combat([fighter1, fighter2])
```

Supports action queues, status effects, resistances

Fully pluggable and extendable

Running Tests
Install test dependencies:
```bash
pip install -r requirements-test.txt
pip install -e .
```
If these packages are not installed before running `pytest`, test collection will fail with import errors for Django/Evennia.
Then run:

```bash
pytest -q
```

Area JSON Format
Room VNUMs now tracked in world/prototypes/areas/*.json under a rooms list. See docs/area_json.md for format details.


## Admin Tools
Use `@whoip` to list connected sessions along with IP and protocol. Provide a search
term to filter by account name or IP.

## Troubleshooting

If `evennia start` fails with "Another twistd server is running", stale
processes or files may be left over. Launch the included helper script to
clean up and start the server again:

```bash
python start_evennia.py
```

The script removes stale PID files, kills any orphaned twistd processes and
frees port 4005 before calling `evennia start`. Both `start_evennia.py` and
`reset_evennia.py` default to port `4005`. Set the `EVENNIA_PORT`
environment variable or pass `--port <num>` to override this value. If Evennia
is already running the script simply prints a warning and exits.

Cleaning up these processes and files usually resolves the error.
