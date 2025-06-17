# Area JSON Files

Area definitions are stored under `world/prototypes/areas` as JSON. Each area file tracks the range of allowed room VNUMs and other metadata.

As of the latest update, area data also includes a `rooms` list containing the VNUMs of rooms explicitly associated with the area. Older area files may not include this key. When loaded those entries will receive an empty list automatically and will continue to work.

If you want to track which rooms belong to an area, use the `aedit add <area> <room_vnum>` command. This not only appends the room VNUM to the area's `rooms` list but also stores the area name on the room prototype. If the VNUM lies outside the area's current range, the command expands the range automatically. Remember to save your changes with `asave changed` when you are done.

Example:

```
aedit add town 2001
asave changed
```

Rooms intended for grid-based maps should also include an `xyz` coordinate.
This triplet `(x, y, "area")` determines where the room appears on the 3×3
minimap shown when players `look`. Set `xyz` on the prototype or through
`redit` to ensure the room is placed correctly.
