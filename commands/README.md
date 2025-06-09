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

* `@mcreate <key> [copy_key]` – make a new prototype, optionally copying an
  existing one.
* `@mset <key> <field> <value>` – update a field on a prototype. Valid races,
  classes and flag names can be found in `world/mob_constants.py`.
* `@mstat <key>` – view the details of a prototype or an existing NPC.
* `@mlist [/room|/area] [filters]` – list prototypes or spawned NPCs. Filters can
  include `class=<val>`, `race=<val>`, `role=<val>`, `tag=<val>`, `zone=<name>`,
  an area name or a numeric/letter range.

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

