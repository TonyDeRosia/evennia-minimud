"""Helper utilities for starting or resetting the Evennia server."""

from __future__ import annotations

import glob
import os
import shutil
import signal
import subprocess
from typing import List, Dict


def _twistd_processes() -> List[Dict[str, str]]:
    """Return a list of running twistd processes as dictionaries."""
    try:
        output = subprocess.check_output(["ps", "axo", "pid,ppid,state,command"], text=True)
    except subprocess.CalledProcessError:
        return []

    procs: List[Dict[str, str]] = []
    for line in output.strip().splitlines()[1:]:
        parts = line.strip().split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, state, cmd = parts
        if "twistd" in cmd:
            procs.append({"pid": int(pid), "ppid": int(ppid), "state": state, "cmd": cmd})
    return procs


def _kill_defunct_parents(procs) -> None:
    """Kill parents of defunct twistd processes."""
    for proc in procs:
        if "<defunct>" in proc["cmd"] or "Z" in proc["state"]:
            try:
                os.kill(proc["ppid"], signal.SIGKILL)
            except ProcessLookupError:
                pass


def _cleanup_files() -> None:
    """Remove stale pid files, logs and twistd temp directories."""
    for pattern in ["server/*.pid", "server/*.log", ".twistd-*"]:
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass


def kill_port(port: int) -> None:
    """Kill any process listening on the given port."""
    try:
        output = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return
    for pid in output.strip().splitlines():
        try:
            os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
