#!/usr/bin/env python3
"""Clean startup helper for Evennia.

The default launcher occasionally leaves behind ``twistd`` processes or
PID files that prevent the game from booting.  This script performs a
more thorough cleanup and then executes ``evennia start``.  It can also
optionally run migrations and reload the server if it is already
running.
"""

import argparse
import glob
import os
import shutil
import signal
import socket
import subprocess
import sys
import time

PORT = 4005
WAIT_TIMEOUT = 15


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


def _wait_for_port(port: int, timeout: int = WAIT_TIMEOUT) -> bool:
    """Return ``True`` when the TCP ``port`` opens or ``False`` if timed out."""
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("localhost", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def _run(cmd: list[str]) -> None:
    """Run a subprocess, printing the command."""
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


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
    parser = argparse.ArgumentParser(description="Clean Evennia startup helper")
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run 'evennia migrate' before starting",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload if the server is already running",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Stop a running server before starting",
    )
    args = parser.parse_args()

    procs = _twistd_processes()
    _kill_defunct_parents(procs)

    running = _is_running()

    if running:
        if args.reload:
            _run(["evennia", "reload"])
            return
        if not args.force:
            print("Evennia already running.")
            return
        _run(["evennia", "stop"])

    if args.migrate:
        _run(["evennia", "migrate"])

    _cleanup_files()
    _kill_port(PORT)

    try:
        _run(["evennia", "start"])
    except FileNotFoundError:
        print("evennia executable not found.", file=sys.stderr)
        sys.exit(1)

    if _wait_for_port(PORT):
        print("Evennia started successfully.")
    else:
        print("Server did not become ready in time.", file=sys.stderr)


if __name__ == "__main__":
    main()
