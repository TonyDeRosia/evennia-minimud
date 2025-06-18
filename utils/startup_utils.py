"""Helpers used by startup scripts."""

from __future__ import annotations

import os
import signal
import subprocess


def kill_port(port: int) -> None:
    """Terminate processes bound to ``port`` if possible."""

    try:  # prefer psutil when available
        import psutil  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        psutil = None

    if psutil:
        for proc in psutil.process_iter(["pid", "connections"]):
            try:
                for conn in proc.connections(kind="inet"):
                    if conn.laddr and conn.laddr.port == port:
                        try:
                            proc.kill()
                        finally:
                            break
            except Exception:
                continue
        return

    if os.name == "posix":
        try:
            output = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return
        for pid in output.strip().splitlines():
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        return

    if os.name == "nt":  # Windows
        try:
            output = subprocess.check_output(["netstat", "-ano"], text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return
        for line in output.splitlines():
            if f":{port} " in line:
                pid = line.split()[-1]
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except subprocess.CalledProcessError:
                    pass

