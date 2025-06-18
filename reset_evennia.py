#!/usr/bin/env python3
"""Reset and restart Evennia server if not already running."""

import os
import subprocess
import sys

from utils.startup_utils import (
    _cleanup_files,
    _kill_defunct_parents,
    _twistd_processes,
    kill_port,
)

PORT = 4005


def evennia_running(procs):
    if any("<defunct>" not in p["cmd"] for p in procs):
        return True
    if os.path.exists("server/server.pid") or os.path.exists("server/portal.pid"):
        return True
    return False


def main():
    procs = _twistd_processes()
    _kill_defunct_parents(procs)
    if evennia_running(procs):
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
