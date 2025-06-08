"""Example scripted AI callbacks."""

from random import choice


def patrol_ai(npc):
    """Simple patrol behavior that moves randomly."""
    if not npc.location:
        return
    exits = npc.location.contents_get(content_type="exit")
    if exits:
        exit_obj = choice(exits)
        exit_obj.at_traverse(npc, exit_obj.destination)
