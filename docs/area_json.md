# Area JSON Files

Area definitions are stored under `world/prototypes/areas` as JSON. Each area file tracks the range of allowed room VNUMs and other metadata.

As of the latest update, area data also includes a `rooms` list containing the VNUMs of rooms explicitly associated with the area. Older area files may not include this key. When loaded those entries will receive an empty list automatically and will continue to work.

If you want to track which rooms belong to an area, use the `aedit add <area> <room_vnum>` command to populate the list and then save the area with `asave changed`.
