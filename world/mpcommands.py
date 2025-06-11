from __future__ import annotations

"""Utility for executing simple mob program commands."""

from evennia import create_object
from evennia.utils import delay
from evennia.prototypes import spawner

from utils.mob_proto import spawn_from_vnum
from utils.prototype_manager import load_prototype

__all__ = ["execute_mpcommand"]


def execute_mpcommand(mob, command: str) -> None:
    """Parse and execute an MP command string for ``mob``.

    Only a subset of traditional mobprog commands are supported.
    Unknown commands are executed directly on the mob.
    """
    if not command:
        return

    parts = command.strip().split(None, 1)
    subcmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if subcmd == "echo":
        if mob.location:
            mob.location.msg_contents(arg)
        return

    if subcmd == "goto":
        dest = mob.search(arg)
        if dest:
            mob.move_to(dest, quiet=True)
        return

    if subcmd == "purge":
        target = mob.search(arg)
        if target:
            target.delete()
        return

    if subcmd == "mload":
        try:
            vnum = int(arg.strip())
        except (TypeError, ValueError):
            return
        spawn_from_vnum(vnum, location=mob.location)
        return

    if subcmd == "oload":
        try:
            vnum = int(arg.strip())
        except (TypeError, ValueError):
            return
        proto = load_prototype("object", vnum)
        if proto:
            obj = spawner.spawn(proto)[0]
            obj.location = mob.location
        return

    if subcmd == "transfer":
        targ_name, _, dest_name = arg.partition(" ")
        target = mob.search(targ_name.strip())
        dest = mob.search(dest_name.strip())
        if target and dest:
            target.move_to(dest, quiet=True)
        return

    if subcmd == "force":
        targ_name, _, cmd = arg.partition(" ")
        target = mob.search(targ_name.strip())
        if target and cmd:
            target.execute_cmd(cmd.strip())
        return

    if subcmd == "delay":
        try:
            ticks, rest = arg.split(" ", 1)
        except ValueError:
            return
        try:
            ticks = int(ticks)
        except ValueError:
            return
        delay(ticks, mob.execute_cmd, rest)
        return

    # default: run raw command on mob
    mob.execute_cmd(f"{subcmd} {arg}".strip())
