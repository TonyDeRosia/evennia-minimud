#!/usr/bin/env python3
"""Reset and restart Evennia server if not already running."""

import os
import subprocess
import signal
import glob
import shutil
import sys

PORT = 4005


def get_twistd_processes():
    """Return list of twistd processes as dicts."""
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
            procs.append(
                {
                    "pid": int(pid),
                    "ppid": int(ppid),
                    "state": state,
                    "cmd": cmd,
                }
            )
    return procs


def kill_parent_of_defunct(procs):
    for p in procs:
        if "<defunct>" in p["cmd"] or "Z" in p["state"]:
            try:
                os.kill(p["ppid"], signal.SIGKILL)
            except ProcessLookupError:
                pass


def cleanup_files():
    for pattern in ["server/*.pid", "server/*.log", ".twistd-*"]:
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass


def kill_port(port):
    try:
        output = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return
    for pid in output.strip().splitlines():
        try:
            os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def evennia_running(procs):
    if any("<defunct>" not in p["cmd"] for p in procs):
        return True
    if os.path.exists("server/server.pid") or os.path.exists("server/portal.pid"):
        return True
    return False


def main():
    procs = get_twistd_processes()
    kill_parent_of_defunct(procs)
    if evennia_running(procs):
        print("Evennia already running.")
        return

    cleanup_files()
    kill_port(PORT)

    try:
        subprocess.run(["evennia", "start"], check=True)
    except FileNotFoundError:
        print("evennia executable not found.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
