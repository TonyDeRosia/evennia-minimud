#!/usr/bin/env python3
"""
Utility to cleanly start the Evennia server using `evennia start`.

This script:
- Checks for lingering twistd processes
- Kills defunct twistd parents
- Cleans up stale PID/log files
- Frees the default port (4005)
- Starts Evennia cleanly
"""

import os
import subprocess
import sys
import signal
import shutil
import glob

PORT = 4005


def _twistd_processes():
    """Return a list of running twistd processes as dictionaries."""
    try:
        output = subprocess.check_output(
            ["ps", "axo", "pid,ppid,state,command"], text=True
        )
    except subprocess.CalledProcessError:
        return []

    procs = []
    for line in output.strip().splitlines()[1:]:
        parts = line.strip().split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, state, cmd = parts
        if "twistd" in cmd:
            procs.append({"pid": int(pid), "ppid": int(ppid), "state": state, "cmd": cmd})
    return procs


def _kill_defunct_parents(procs):
    """Kill the parent of any defunct (zombie) twistd processes."""
    for p in procs:
        if "<defunct>" in p["cmd"] or "Z" in p["state"]:
            try:
                os.kill(p["ppid"], signal.SIGKILL)
            except ProcessLookupError:
                pass


def _cleanup_files():
    """Remove stale .pid, .log, and twistd temp files."""
    for pattern in ["server/*.pid", "server/*.log", ".twistd-*"]:
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass


def kill_port(port: int):
    """Kill any process listening on the specified port."""
    try:
        output = subprocess.check_output(
            ["lsof", "-i", f":{port}"], text=True
        ).splitlines()[1:]  # skip header
        for line in output:
            parts = line.split()
            if len(parts) >= 2:
                pid = int(parts[1])
                os.kill(pid, signal.SIGKILL)
    except subprocess.CalledProcessError:
        pass  # lsof returned no output


def _is_running() -> bool:
    """Check if Evennia appears to be already running."""
    return os.path.exists("server/server.pid") or os.path.exists("server/portal.pid")


def main() -> None:
    procs = _twistd_processes()
    _kill_defunct_parents(procs)

    if _is_running():
        print("Evennia already running.")
        return

    _cleanup_files()
    kill_port(PORT)

    try:
        subprocess.run(["evennia", "start"], check=True)
    except FileNotFoundError:
        print("evennia executable not found.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
