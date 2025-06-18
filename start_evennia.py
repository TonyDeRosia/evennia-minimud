#!/usr/bin/env python3
"""Utility to cleanly start the Evennia server using ``evennia start``.

This script checks for lingering processes or files that might prevent
Evennia from launching. It removes stale PID files and temporary
directories and frees the configured port before executing
``evennia start``. The port defaults to ``4005`` but can be overridden by
setting the ``EVENNIA_PORT`` environment variable or by passing
``--port`` on the command line.
"""

import argparse
import glob
import os
import shutil
import signal
import subprocess
import sys

PORT = 4005


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanly start Evennia")
    parser.add_argument(
        "--port",
        type=int,
        help="TCP port to free before starting",
    )
    return parser.parse_args()


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
    for p in procs:
        if "<defunct>" in p["cmd"] or "Z" in p["state"]:
            try:
                os.kill(p["ppid"], signal.SIGKILL)
            except ProcessLookupError:
                pass


def _cleanup_files():
    for pattern in ["server/*.pid", "server/*.log", ".twistd-*"]:
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass


def _kill_port(port: int):
    try:
        output = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return
    for pid in output.strip().splitlines():
        try:
            os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def _is_running() -> bool:
    return os.path.exists("server/server.pid") or os.path.exists("server/portal.pid")


def main() -> None:
    args = _parse_args()
    port = args.port if args.port is not None else int(os.getenv("EVENNIA_PORT", PORT))

    procs = _twistd_processes()
    _kill_defunct_parents(procs)

    if _is_running():
        print("Evennia already running.")
        return

    _cleanup_files()
    _kill_port(port)

    try:
        subprocess.run(["evennia", "start"], check=True)
    except FileNotFoundError:
        print("evennia executable not found.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
