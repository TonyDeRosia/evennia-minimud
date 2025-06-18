#!/usr/bin/env python3
"""
Reset and restart the Evennia server if it's not already running.

This script:
- Detects existing twistd processes.
- Kills defunct twistd parents.
- Cleans up stale log and PID files.
- Frees port 4005 (or override via EVENNIA_PORT).
- Starts Evennia cleanly.
"""

import os
import subprocess
import sys

from utils.startup_utils import (
    _cleanup_files,
    _kill_defunct_parents,
    _twistd_processes,
    kill_port,
)

DEFAULT_PORT = 4005


def evennia_running(procs) -> bool:
    """Determine if Evennia is already running."""
    if any("<defunct>" not in p["cmd"] for p in procs):
        return True
    if os.path.exists("server/server.pid") or os.path.exists("server/portal.pid"):
        return True
    return False


def main():
    port = int(os.getenv("EVENNIA_PORT", DEFAULT_PORT))
    procs = _twistd_processes()
    _kill_defunct_parents(procs)

    if evennia_running(procs):
        print("Evennia is already running.")
        return

    _cleanup_files()
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
