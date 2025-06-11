# commands/

This folder holds modules for implementing one's own commands and
command sets. All the modules' classes are essentially empty and just
imports the default implementations from Evennia; so adding anything
to them will start overloading the defaults. 

You can change the organisation of this directory as you see fit, just
remember that if you change any of the default command set classes'
locations, you need to add the appropriate paths to
`server/conf/settings.py` so that Evennia knows where to find them.
Also remember that if you create new sub directories you must put
(optionally empty) `__init__.py` files in there so that Python can
find your modules.

## Dig Command

The `dig` command creates a new room in the given compass direction and
links exits between the current location and the new room. Usage:

```
dig <direction>
```

For example, `dig north` will make a new room north of the current one
and also create a south exit back.

## Room Editing Commands

Builders can tweak the current room with a few simple commands:

* `rrename <new name>` - change the room's name. Aliases: `roomrename`,
  `renameroom`, `rname`.
* `rdesc <new description>` - set the room's description. With no
  argument it will show the current description.
* `rset area <area>` or `rset id <number>` - assign the room to an
  area or change its id within that area.
* `rreg <area> <number>` or `rreg <room> <area> <number>` - register a
  room to an area and numeric id.

## Object Editing Commands

Builders and admins can adjust object attributes with these commands:

* `setdesc <target> <description>` - change an object's description.
* `setweight <target> <value>` - assign a numeric carry weight.
* `setslot <target> <slot>` - set the slot or clothing type.
* `setdamage <target> <amount>` - set the object's damage value.
* `setbuff <target> <buff>` - label the object with a buff identifier.

## Object Creation Commands

* `cweapon <name> <slot> <damage> [weight] [stat_mods] <description>` - create a
  melee weapon in your inventory. Modifiers use `Stat+Value`, comma separated,
  and multiword or ANSI-coloured names must be quoted. The item's key stays
  exactly as typed. A
  lowercase alias plus a numbered alias like `name-1`, `name-2`, and so forth is
  added silently for each item with the same name.

## Inspect Command

Use `inspect <item>` to view an object's details. The command accepts the
numbered aliases created for duplicates, so you can inspect a specific item
even when many share the same key. For instance, `inspect epee-2` will show the
stats, slot and any effects of the second "Epee" you made.

## NPC Prototype Commands

NPCs are saved as prototypes in `world/prototypes/npcs.json` and can be
spawned later with `@spawnnpc`. These commands help you manage the prototypes:

*A role describes what the NPC does (merchant, questgiver...),*
*while the class selects the NPC typeclass (base, merchant, banker...).*
*After picking the NPC class, the mob builder also lets you choose a*
*combat class like Warrior or Mage which sets `npc.db.charclass`.*

* `@mcreate <key> [copy_key]` – make a new prototype, optionally copying an
  existing one.
* `@mset <key> <field> <value>` – update a field on a prototype. Valid races,
  classes and flag names can be found in `world/mob_constants.py`.
* `@mstat <key>` – view the details of a prototype or an existing NPC.
* `@mlist [/room|/area] [filters]` – list prototypes or spawned NPCs. Results
  include a VNUM column when one is registered. Filters can include
  `class=<val>`, `race=<val>`, `role=<val>`, `tag=<val>`, `zone=<name>`, an area
  name or a numeric/letter range. When called with no arguments the command
  also displays a **Finalized VNUMs** section showing every VNUM stored in the
  mob database.

Example:

```text
@mcreate goblin
@mset goblin desc "A sneaky goblin"
@mset goblin level 2
@mstat goblin
```

## Shop and Repair Setup

Merchants and smiths use extra data stored on their prototypes. Create the
sections with `@makeshop` and `@makerepair` and then configure them with
`@shopset` and `@repairset`.

```text
@mcreate trader
@makeshop trader
@shopset trader buy 150
@shopset trader sell 50
@shopset trader hours 8-18
@shopset trader types weapon,armor

@mcreate smith
@makerepair smith
@repairset smith cost 200
@repairset smith hours 9-21
@repairset smith types weapon
```

Use `@shopstat <proto>` or `@repairstat <proto>` to review the settings.


## Importing and Exporting

Use `@mobexport <proto> <file>` to write a prototype to JSON in the
`PROTOTYPE_NPC_EXPORT_DIR` directory. Load a file with
`@mobimport <file>` which will register or replace that prototype.

```text
@mobexport goblin goblin.json
@mobimport goblin.json
```

## Prototype Diffing

The `Builder` command set also includes `@mobproto` for managing
numbered mob prototypes. Use the `diff` subcommand to compare any two
entries:

```text
@mobproto diff 1 2
```

This shows a table of key/value pairs from each prototype with differing
fields highlighted.

Delete a prototype with `@mobproto delete <vnum>`. Deletion will fail if any
live NPCs spawned from that VNUM still exist.

## VNUM Utility

Use `@nextvnum` to reserve the next available VNUM for a type of object. The
argument selects the category:

```
@nextvnum <I|M|R|O|Q|S>
```

* **I** or **O** – object/item VNUM
* **M** – mob/NPC VNUM
* **R** – room VNUM
* **Q** – quest VNUM
* **S** – script VNUM

The returned number is automatically marked as used in the registry.

## VNUM Prefixes

Numbers may be referenced with a single letter prefix indicating the
category.  ``M`` is used for mobs, ``O`` or ``I`` for objects, ``R`` for rooms,
``Q`` for quests and ``S`` for scripts.  For example ``M200001`` refers to the
mob prototype with VNUM ``200001``.  The prefix form works anywhere a command
expects a prototype key and avoids confusion with other numeric arguments.

## Automatic Assignment in the Mob Builder

When using the menu driven mob builder you may enter ``auto`` at the VNUM
prompt. This calls ``@nextvnum M`` behind the scenes and registers the number
immediately.  Prototypes saved from the builder use the ``mob_`` prefix and any
NPC spawned from a VNUM prototype receives a ``M<number>`` tag.  You can search
for live NPCs with ``search_tag(key="M<number>", category="vnum")``.
