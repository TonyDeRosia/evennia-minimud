from __future__ import annotations

"""Utility for executing simple mob program commands."""

from importlib import import_module

from evennia import create_object
from evennia.utils import delay
from evennia.prototypes import spawner

from utils.mob_proto import spawn_from_vnum
from utils.prototype_manager import load_prototype
from utils.eval_utils import eval_safe
from world.system import state_manager

__all__ = ["execute_mpcommand"]


def _run_single(mob, command: str) -> None:
    """Execute a single mpcommand without condition handling."""

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
        try:
            spawn_from_vnum(vnum, location=mob.location)
        except ValueError:
            return
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

    if subcmd == "cast":
        spell = arg
        target_name = None
        if " on " in arg:
            spell, target_name = arg.split(" on ", 1)
        elif " " in arg:
            spell, target_name = arg.split(" ", 1)
        spell = spell.strip().strip("'\"")
        target = mob.search(target_name.strip()) if target_name else None
        if hasattr(mob, "cast_spell") and spell:
            mob.cast_spell(spell.lower(), target=target)
        return

    if subcmd == "mpdamage":
        targ_name, _, rest = arg.partition(" ")
        target = mob.search(targ_name.strip())
        amount_str, _, dtype = rest.partition(" ")
        try:
            amount = int(amount_str)
        except (TypeError, ValueError):
            return
        if target and getattr(target, "traits", None) and callable(getattr(target, "at_damage", None)):
            target.at_damage(mob, amount, damage_type=dtype or None)
        return

    if subcmd == "mpapply":
        targ_name, _, rest = arg.partition(" ")
        target = mob.search(targ_name.strip())
        effect, _, dur = rest.partition(" ")
        try:
            duration = int(dur) if dur else 1
        except ValueError:
            duration = 1
        if target and effect:
            state_manager.add_effect(target, effect.strip(), duration)
        return

    if subcmd == "mpcall":
        path = arg.strip()
        if path:
            module, func = path.rsplit(".", 1)
            mod = import_module(module)
            getattr(mod, func)(mob)
        return

    if subcmd == "kill":
        target = mob.search(arg)
        if target and hasattr(mob, "enter_combat"):
            mob.enter_combat(target)
        return

    # default: run raw command on mob
    mob.execute_cmd(f"{subcmd} {arg}".strip())


def execute_mpcommand(mob, commands: str | list[str]) -> None:
    """Execute one or multiple MP commands with simple conditionals."""

    if not commands:
        return

    if isinstance(commands, str):
        parts: list[str] = []
        for line in commands.splitlines():
            parts.extend(x.strip() for x in line.split(";") if x.strip())
        commands = parts

    idx = 0
    stack: list[dict] = []
    while idx < len(commands):
        cmd = commands[idx].strip()
        lcmd = cmd.lower()

        if lcmd.startswith("if "):
            cond = bool(eval_safe(cmd[3:].strip(), {"mob": mob}))
            stack.append({"cond": cond, "execute": cond})
            idx += 1
            continue

        if lcmd == "else":
            if stack:
                frame = stack[-1]
                frame["execute"] = not frame["cond"]
            idx += 1
            continue

        if lcmd == "endif":
            if stack:
                stack.pop()
            idx += 1
            continue

        if lcmd == "break":
            if stack:
                depth = len(stack)
                target_depth = depth - 1
                stack.pop()
                idx += 1
                while idx < len(commands):
                    ncmd = commands[idx].strip().lower()
                    if ncmd.startswith("if "):
                        depth += 1
                    elif ncmd == "endif":
                        depth -= 1
                        if depth == target_depth:
                            idx += 1
                            break
                    idx += 1
                continue
            break

        if lcmd == "return":
            break

        if all(frame.get("execute", True) for frame in stack):
            _run_single(mob, cmd)

        idx += 1
