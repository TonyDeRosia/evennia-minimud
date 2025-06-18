#!/usr/bin/env python3
"""
Cleanly start the Evennia server by ensuring all stale processes, PID files,
and logs are removed. Frees up the configured port and then runs `evennia start`.

Usage:
    python reset_evennia.py [--port 4005]

Environment:
    EVENNIA_PORT - Overrides the default port if set.
"""

import argparse
import glob
import os
import shutil
import signal
import subprocess
import sys

from utils.startup_utils import kill_port


DEFAULT_PORT = 4005


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanly start the Evennia server.")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("EVENNIA_PORT", DEFAULT_PORT)),
        help="TCP port to free before starting (default: 4005 or from $EVENNIA_PORT)."
    )
    return parser.parse_args()


def find_twistd_processes():
    """Find all running twistd-related processes."""
    try:
        output = subprocess.check_output(["ps", "axo", "pid,ppid,state,command"], text=True)
    except subprocess.CalledProcessError:
        return []

    processes = []
    for line in output.strip().splitlines()[1:]:
        parts = line.strip().split(None, 3)
        if len(parts) == 4 and "twistd" in parts[3]:
            pid, ppid, state, cmd = parts
            processes.append({
                "pid": int(pid),
                "ppid": int(ppid),
                "state": state,
                "cmd": cmd
            })
    return processes


def kill_defunct_parent_processes(processes):
    for proc in processes:
        if "<defunct>" in proc["cmd"] or "Z" in proc["state"]:
            try:
                os.kill(proc["ppid"], signal.SIGKILL)
            except ProcessLookupError:
                pass


def clean_temp_files():
    for pattern in ["server/*.pid", "server/*.log", ".twistd-*"]:
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.remove(path)
                except FileNotFoundError:
                    continue


def evennia_is_running() -> bool:
    return any(os.path.exists(f) for f in ("server/server.pid", "server/portal.pid"))


def main():
    args = parse_args()
    port = args.port

    procs = find_twistd_processes()
    kill_defunct_parent_processes(procs)

    if evennia_is_running():
        print("Evennia is already running.")
        return

    clean_temp_files()
    kill_port(port)

    try:
        subprocess.run(["evennia", "start"], check=True)
    except FileNotFoundError:
        print("Error: 'evennia' command not found.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Evennia failed to start: {e}", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
