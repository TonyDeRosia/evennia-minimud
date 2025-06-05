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

## Object Editing Commands

Builders and admins can adjust object attributes with these commands:

* `setdesc <target> <description>` - change an object's description.
* `setweight <target> <value>` - assign a numeric carry weight.
* `setslot <target> <slot>` - set the slot or clothing type.
* `setdamage <target> <amount>` - set the object's damage value.
* `setbuff <target> <buff>` - label the object with a buff identifier.
