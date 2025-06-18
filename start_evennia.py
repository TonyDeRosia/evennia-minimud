#!/usr/bin/env python3
"""Utility to cleanly start the Evennia server using `evennia start`.

This script checks for lingering processes or files that might prevent
Evennia from launching. It removes stale PID files and temporary
directories and frees the default port before executing ``evennia start``.
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

PORT = 4005


def _is_running() -> bool:
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
