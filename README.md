# Evennia: The RPG


### What is this?

Evennia is a game engine/framework for making online multiplayer text games, such as MUDs.

*This* game is an attempt to make a small but fully-functional RPG-style MUD with as little custom code as possible, relying as much as possible on the existing community-contributed packages. 

### Okay... but why?

I wanted to see just how doable it would be for a brand new game developer to get a typical full game out the door - both for my own curiosity, and to show to other people who might want to make their own games!

One of the selling points of Evennia, besides how flexible and easy to customize it is, is the fact that you can have a server set up and online within minutes. But part of that "flexible and easy to customize" angle means that it tries to be as unopinionated as possible and have as few of the kinds of mechanics that make a game unique defined out of the box. The community contribs, on the other hand, are stand-alone add-ons that can be as opinionated as the contributors want, so if they suit your game vision, you can just put them right in.

### Can I use this to make my own game?

Yes!! Please do! There's installation instructions further down, and be sure to check out the [Evennia website](https://evennia.com).

### This game is okay but it would be better if it had <something else>....

You are absolutely correct!

Since my goal was to write as little custom code as possible, most of the mechanics are as minimal as I could get away with. But the code is all here and free for the taking - if you like part of it but want it to be better, make it better!


## Coins and Currency

This game uses four types of coins. They convert as follows:

```
1 Silver = 100 Copper
1 Gold  = 10 Silver  = 1,000 Copper
1 Platinum = 100 Gold = 1,000 Silver = 100,000 Copper
```

Typical uses for each coin are roughly:

- **Copper** – everyday expenses like a meal or a night at a cheap inn.
- **Silver** – standard goods, basic gear or routine services.
- **Gold** – quality equipment or costly services such as a house or mount.
- **Platinum** – rare, high value purchases or very large transactions.

Bankers can hold your coins for safekeeping. When near one, use the `bank`
command to check your balance, deposit or withdraw funds, or transfer money to
another player:

```
bank balance
bank deposit <amount [coin]>
bank withdraw <amount [coin]>
bank transfer <amount [coin]> <player>
```


## Installation and Setup

I set this up to make it reasonably easy to install and set up, but I had to make a decision between "write a bunch more code" and "add a couple more steps" and since my goal was to write *less* code.... Well, you've got a couple more steps.

First, you need to install Python 3.12 and have git in your command line. Then, cd to your programming folder (or make one and cd in) and follow these steps to download and install:

*(If you know what any of the steps do and want to do them differently, feel free.)*

#### Windows
```
git clone https://github.com/InspectorCaracal/evennia-minimud.git
cd evennia-minimud
py -m venv .venv
.venv\Scripts\activate
pip install .
py -m evennia
evennia migrate
evennia start
```

#### Linux & Mac
```
git clone https://github.com/InspectorCaracal/evennia-minimud.git
cd evennia-minimud
python -m venv .venv
source .venv/bin/activate
pip install .
evennia migrate
evennia start
```

That last step will prompt you to set up an initial admin, or superuser, account for the game. It also creates an initial test character.

*If you forget your password, you can change it from outside the game with `evennia changepassword youraccount` at any time - just make sure to reload the game with `evennia reload` so it will take effect.*

Once you've done that and it finishes starting up, set up the XYZGrid map plugin and the starter town with the following:

```
evennia xyzgrid init
evennia xyzgrid add world.maps.starter_town
evennia xyzgrid spawn
```

Enter `Y` to start the map building, wait a bit for that to finish, then:

    evennia reload
		
Finally, open your web browser and go to `localhost:4001` to get to the game's webpage, log in, and then click the big `Play in the browser!` button....

You're connected to the game! Use the `ic` command to connect to your test character in order to finish the last piece of setup. Once you're in Limbo, enter:

    batchcmd initial_build

to create the "overworld" map and do some finishing touches to the town's set-up.

## Building your Own Game

You want to make your own game? Awesome! The code here should help give you something to start from, but you should also check out the excellent Evennia docs - especially the [tutorial walkthrough](https://www.evennia.com/docs/latest/Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.html). It covers working with Evennia, developing within Evennia, and a walkthrough of building a full game within Evennia. (It's still in-progress but is *mostly* complete.)

If you wind up having any issues or questions working with Evennia, [the Discord community](https://discord.gg/AJJpcRUhtF) is small but active and there's almost always someone around who's happy to help newcomers.

### NPC Creation Menu

You can quickly set up non-player characters using `cnpc start <key>` (alias
`createnpc`). This opens an interactive menu where you enter the key,
description, type, level and other details. Follow the prompts, review the summary at the end
and confirm to create your NPC. You can later update them with `cnpc edit
<npc>`.

See the `cnpc` help entry for a full breakdown of every menu option.

The builder lets you choose an NPC type such as `merchant`, `banker`,
`trainer`, `wanderer` or `combatant`. These map to the typeclasses under
`typeclasses.npcs`. When you select the `combatant` type you'll be asked
for a combat class from `world.scripts.classes`; this sets
`npc.db.charclass` on the spawned NPC. Combatants use the
`typeclasses.npcs.combat.CombatNPC` class which automatically sets
`npc.db.can_attack = True`.

While editing, there's a step to manage triggers using a numbered menu. Choose
`Add trigger` to create a new reaction, `Delete trigger` to remove one, `List
triggers` to review them and `Finish` when done. Multiple trigger entries can be
added for the same event. When entering a reaction you may separate several
commands with commas or semicolons to store them as multiple responses. See the
`triggers` help entry for the list of events and possible reactions.

### NPC Roles and AI

The builder lets you assign one or more roles and basic AI scripts. Roles are
mixins found under `world.npc_roles`:

- **merchant** – sells items to players.
- **banker** – handles deposits and withdrawals.
- **trainer** – teaches skills.
- **guildmaster** – manages guild business.
- **guild_receptionist** – greets visitors for a guild.
- **questgiver** – offers quests to players.
- **guard** – protects areas or important figures.
- **combat_trainer** – spars to improve combat ability.
- **event_npc** – starts or manages special events.

AI behaviors come from `world.npc_handlers.ai` and can be selected in the
builder:

- **passive** – take no automatic actions.
- **aggressive** – attack the first player seen.
- **defensive** – fight back only when in combat.
- **wander** – roam randomly through available exits.
- **scripted** – runs the callback stored in ``npc.db.ai_script``.

For scripted AI you must assign a callable to ``npc.db.ai_script``. This can be
either a Python import path or a direct function reference. Callbacks must live
under the ``scripts`` package. Example::

    npc.db.ai_script = "scripts.example_ai.patrol_ai"

You can also attach full Script typeclasses to mobs. After selecting languages in
the mob builder you will be prompted for a script path such as
``scripts.bandit_ai.BanditAI``. When saved as a prototype this is stored under
``scripts`` and automatically started when the mob spawns.

### Trigger Syntax

NPC triggers use a dictionary mapping events to one or more reaction entries. A
reaction may specify a `match` text and single or multiple `responses` to run::

    {
        "on_enter": [
            {"match": "", "responses": ["say Hello", "emote waves"]}
        ]
    }

During the builder you can add triggers one at a time. The example above shows
how multiple responses can be combined in your prototype file or entered during
the builder by separating commands with commas or semicolons.

To spawn an NPC saved with an AI type and triggers, use:

```text
@spawnnpc my_npc_proto
```

There are also helper commands for managing NPCs after creation:
`@editnpc <npc>` reopens the builder on an existing NPC, `@clonenpc <npc> [= <new_name>]`
duplicates one, `@deletenpc <npc>` removes it (with confirmation) and
`@spawnnpc <proto>` spawns a saved prototype from `world/prototypes/npcs.json`.
You can organize prototypes by area with `@listnpcs <area>`, spawn them with
`@spawnnpc <area>/<proto>` and duplicate them using
`@dupnpc <area>/<proto> [= <new_key>]`. Saving a prototype while standing in a
room that has an `area` set automatically adds it to that area's list.

Several basic NPC prototypes are included out of the box. Try `cnpc dev_spawn basic_merchant`
or `@spawnnpc basic_merchant` to quickly create a merchant, or `basic_questgiver` for a quest
giver.

### Mob Program Commands

Triggers can run mob program commands to control NPCs. Useful actions include:

- `mob mpdamage <target> <amount> [type]` – deal damage to a target.
- `mob mpapply <target> <effect> [duration]` – apply a timed status effect.
- `mob mpcall <module.func>` – invoke a Python callback.

Conditional logic is also available using `if`, `else` and `endif` along with
`break` and `return` to control flow::

    if rand(50)
        mob echo Lucky!
    else
        mob echo Unlucky...
    endif

### Object and Room Programs

Objects and rooms can have simple programs attached as well. The `opedit`
and `rpedit` commands add an entry to an object or room prototype by VNUM.
After entering the number you specify the event name and the command to run.
For example::

    opedit 100001
    on_use
    say It glows brightly.

Programs are saved under `objprogs` or `roomprogs` on the prototype and are
converted to triggers when the object or room spawns.

### NPC Prototypes

A prototype is a JSON record stored in `world/prototypes/npcs.json` describing
all of an NPC's settings such as stats, roles, triggers and AI. When you finish
the builder, selecting **Yes** spawns the NPC in your current location.
Choosing **Yes & Save Prototype** spawns the NPC and writes the prototype to
that file so you can recreate it later. In this context **prototype** means the
saved blueprint of the NPC. The **archetype**, set by the `NPCType` field in the
builder, defines the NPC's overall role or behavior such as *merchant* or
*combatant*.

You can spawn a saved prototype at any time with `@spawnnpc <key>`. Prototypes
made with `mobbuilder` are automatically given the `mob_` prefix. Use
`@mspawn mob_<key>` or `@mspawn M<vn>` to create additional copies of those
mobs when a VNUM has been assigned.

### Mob Builder

`mobbuilder` is now an alias for the unified `cnpc` command. It launches the
same menu with mob defaults and immediately spawns the NPC once you confirm.
Choosing **Yes & Save Prototype** will also store the entry in
`world/prototypes/npcs.json` with the `mob_` prefix so you can reuse it with
`@mspawn <prototype>` or ``M<number>``. The final summary now shows any mob
specific fields such as act flags and resistances.
If you assign a VNUM when saving, the prototype is automatically registered
for use with ``@mspawn M<number>``.
Before launching `cnpc` or `mobbuilder` you can pre-load a baseline with `@mobtemplate <template>`. This fills the builder with default stats for the chosen template. Run `@mobtemplate list` to view the available presets for all seventeen combat classes such as `warrior`, `mystic`, `wizard`, `ranger` or `swashbuckler` as well as the utility `merchant` template.

Only NPCs with `can_attack` set to `True` can be attacked. The new `CombatNPC` class (used for the `combatant` type) sets this flag automatically so mobs are immediately ready for battle.

Example::

    cnpc start goblin
    [follow the prompts]
    [choose **Yes & Save Prototype**]
    @mspawn mob_goblin
    @mspawn M200001

### Quick Mob

`@quickmob <key> [template]` loads a template from
`world.templates.mob_templates` and opens the NPC builder with those defaults
filled in. A VNUM is reserved automatically so once you finish the builder and
save the prototype you can respawn the mob later with ``@mspawn M<number>``.

Example::

    @quickmob goblin warrior

### MEdit

Use `medit <vnum>` to edit an existing numeric prototype. The command
`medit create <vnum>` reserves the number, loads a basic template and
opens the same builder menu for customization.

## Mob Prototype Manager

`@mobproto` works with numeric VNUMs to store and spawn NPCs. Newly
created entries are added to `@mlist` automatically so you can see them
alongside area prototypes. Common subcommands are:

```text
@mobproto create <vnum> <name>
@mobproto set <vnum> <field> <value>
@mobproto list
@mobproto spawn <vnum>
```

Example:

```text
@mobproto create 1 goblin
@mobproto set 1 level 3
@mobproto spawn 1
```

## Weapon Creation and Inspection

Builders can quickly create melee weapons with the `cweapon` command.

```
cweapon [/unidentified] <name> <slot> <damage> [weight] [stat_mods] <description>
```

Damage may be a flat number or an `NdN` dice value. The item's key never
changes, even if multiple weapons share the same name. Instead, a lowercase
alias and a numbered alias like `name-1`, `name-2`, and so on are added
silently.

These aliases let you reference duplicates. For example:

```text
cweapon "epee" mainhand 1d4 2 STR+1 A sharp epee.
cweapon "epee" offhand 2d6 3 STR+1, Attack Power+2 A balanced offhand blade.
inspect epee-2
```

Modifiers use the form `Stat+Value` separated by commas. Quote names that
contain spaces or ANSI colour codes, as shown above.

Add `/unidentified` before the name to create the weapon unidentified.

When a weapon is identified, `inspect` shows its damage, slot, any bonuses and
effects, so `inspect epee-2` will display the full details of the second
"Epee" you created.
## Combat System

A modular combat engine is provided under the `combat/` package. It implements
round-based processing, action queues and a sample `ShieldBash` skill. The
system is designed to plug into Evennia characters and rooms for dynamic fights.

### Damage Types and Resistances

Damage dealt in combat is categorized by `DamageType`. Characters may hold
resistance flags in their `db.resistances` attribute. During damage resolution the
engine consults a resistance matrix to modify incoming damage. For example:

```python
from combat.damage_types import DamageType, ResistanceType, get_damage_multiplier

mult = get_damage_multiplier([ResistanceType.FIRE], DamageType.FIRE)
print(mult)  # 0.5
```

Resistances can be assigned via the mob builder menu when creating NPCs.

### Status Effects

Many combat abilities apply temporary status conditions. Effects like
`stunned` or `defending` last a set number of combat ticks and may alter
stats or restrict actions. Use the `affects` command or `status` to view
your current buffs and conditions. Effects expire automatically when
their duration reaches zero.

### Hunger & Thirst

If a character's `sated` value reaches zero they gain the `hungry_thirsty`
status effect. Each tick removes 5% of their maximum health, mana and stamina
while this status is active, rather than a single point from each resource.

### AI Settings

NPC behavior is configured by an AI type during `cnpc` or `mobbuilder`.
Choose from `passive`, `aggressive`, `defensive`, `wander` or
`scripted`. Scripted AI runs the callable stored on `npc.db.ai_script`.
These options let builders quickly create enemies that fight or roam on
their own. The combat command set includes `attack`, `wield`, `unwield`,
`flee`, `berserk`, `respawn`, `revive` and `status`.

### Helper Utilities

Convenience functions in `utils.mob_utils` provide building blocks for working
with VNUM-based NPCs.

- `assign_next_vnum(category)` – fetches and reserves the next free VNUM.
- `add_to_mlist(vnum, proto)` – records a prototype in the mob database so it
  appears in `@mlist`.
- `auto_calc(stats)` and `auto_calc_secondary(stats)` – derive combat stats from
  primary values using `world.system.stat_manager`.


## Running the Tests

The test suite requires Evennia and Django in addition to `pytest`. Make sure
these packages are installed before invoking the test runner. The easiest way is
to use the provided requirements file which installs compatible versions of all
three:

```bash
python -m pip install --upgrade pip
pip install -r requirements-test.txt
# Install the project itself so tests can import it
pip install -e .
```

You can also run `scripts/setup_test_env.sh` to automate the above steps.

After installing the dependencies, execute the tests with:

```bash
pytest -q
```

