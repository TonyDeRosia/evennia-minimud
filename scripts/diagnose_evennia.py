#!/usr/bin/env python3
"""Diagnose the Evennia environment for common issues."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from typing import List

from utils.startup_utils import _twistd_processes


def check_evennia_version() -> str:
    """Return the Evennia version or an error message."""
    try:
        out = subprocess.check_output(["evennia", "--version"], text=True)
        return f"Evennia version: {out.strip()}"
    except FileNotFoundError:
        return "Evennia executable not found."
    except subprocess.CalledProcessError as err:
        return f"Failed to run 'evennia --version': {err}"


def check_executable_path() -> str:
    """Verify that the evennia executable on PATH comes from this env."""
    path = shutil.which("evennia")
    if not path:
        return "evennia not found in PATH."
    if os.path.commonpath([path, sys.prefix]) == sys.prefix:
        return f"evennia executable on PATH: {path}"
    return f"evennia executable outside virtualenv: {path}"


def try_imports() -> List[str]:
    """Attempt to import evennia and django."""
    results: List[str] = []
    try:
        import evennia  # noqa: F401
        results.append("Successfully imported evennia")
    except Exception as err:  # pragma: no cover - diagnostic output
        results.append(f"Failed to import evennia: {err}")
    try:
        import django  # noqa: F401
        results.append("Successfully imported django")
    except Exception as err:  # pragma: no cover - diagnostic output
        results.append(f"Failed to import django: {err}")
    return results


def test_database() -> str:
    """Attempt a test database connection."""
    try:
        from django.db import connections

        connections["default"].ensure_connection()
        return "Database connection successful"
    except Exception as err:  # pragma: no cover - diagnostic output
        return f"Database connection failed: {err}"


def list_twistd_processes() -> List[str]:
    """Return info on any running twistd processes."""
    procs = _twistd_processes()
    if not procs:
        return ["No running twistd processes detected"]
    lines = ["Running twistd processes:"]
    for p in procs:
        lines.append(f"  PID {p['pid']} (PPID {p['ppid']}, state {p['state']}): {p['cmd']}")
    return lines


def list_stale_files() -> List[str]:
    """Return a list of any stale pid or log files."""
    patterns = ["server/*.pid", "server/*.log"]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    if not files:
        return ["No stale PID or log files found"]
    lines = ["Stale PID/log files:"]
    for fpath in files:
        lines.append(f"  {fpath}")
    return lines


def main() -> None:
    steps: List[str] = []

    steps.append("Step 1: Check Evennia version")
    steps.append(check_evennia_version())

    steps.append("\nStep 2: Verify evennia executable location")
    steps.append(check_executable_path())

    steps.append("\nStep 3: Attempt imports")
    steps.extend(try_imports())

    steps.append("\nStep 4: Test database connection")
    steps.append(test_database())

    steps.append("\nStep 5: Check for running twistd processes")
    steps.extend(list_twistd_processes())

    steps.append("\nStep 6: Look for stale PID/log files")
    steps.extend(list_stale_files())

    print("\n".join(steps))


if __name__ == "__main__":
    main()

