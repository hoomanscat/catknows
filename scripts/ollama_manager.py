"""Simple manager to start/stop/check a local Ollama process.

Usage:
  python scripts/ollama_manager.py start   # starts ollama (if binary found) and waits for HTTP
  python scripts/ollama_manager.py stop    # stops process started by this script (PID file)
  python scripts/ollama_manager.py status  # check HTTP endpoint
  python scripts/ollama_manager.py ensure  # start if not running

This is intended as a developer convenience only. It expects an `ollama` binary
on PATH or a path set in OLLAMA_BIN. It starts the process, writes a PID file
to .venv/ollama.pid (or ./ollama.pid), and polls the configured REST URL until ready.
"""
from __future__ import annotations
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional

import requests
from urllib.parse import urlparse

PID_FILE = Path('.venv') / 'ollama.pid'
if not PID_FILE.parent.exists():
    PID_FILE = Path('ollama.pid')

DEFAULT_URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434/api/generate')
OLLAMA_BIN = os.getenv('OLLAMA_BIN', 'ollama')


def is_http_ok(url: str = DEFAULT_URL, timeout: float = 2.0) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200 or r.status_code == 404 or r.status_code == 204
    except Exception:
        return False


def find_pid_by_port(url: str = DEFAULT_URL) -> Optional[int]:
    """Return PID listening on the port for the given URL, or None."""
    try:
        parsed = urlparse(url)
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    except Exception:
        return None

    try:
        # Use netstat to find listening PID (works on Windows)
        out = subprocess.check_output(['netstat', '-ano'], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if f':{port} ' in line or f':{port}\t' in line or f':{port}\r' in line:
                parts = line.split()
                if parts:
                    pid_str = parts[-1]
                    try:
                        return int(pid_str)
                    except Exception:
                        continue
    except Exception:
        return None
    return None


def start_ollama(wait_seconds: int = 10) -> Optional[int]:
    # Start the ollama process (simple invocation)
    # If port already bound, reuse that PID
    existing_pid = find_pid_by_port()
    if existing_pid:
        try:
            PID_FILE.write_text(str(existing_pid))
        except Exception:
            pass
        print(f"Detected existing Ollama listening on port; pid={existing_pid}")
        return existing_pid

    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text())
            # check if process exists
            os.kill(pid, 0)
            print(f"Ollama PID {pid} appears to be running")
            return pid
        except Exception:
            PID_FILE.unlink(missing_ok=True)

    bin_path = OLLAMA_BIN
    cmd = [bin_path, 'serve'] if os.name != 'nt' else [bin_path, 'serve']
    # On Windows, launching without shell; leave stdout/stderr as inherited
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(f"Ollama binary not found at '{bin_path}'. Set OLLAMA_BIN or add to PATH.")
        return None
    pid = p.pid
    try:
        PID_FILE.write_text(str(pid))
    except Exception:
        pass

    # wait for http endpoint
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_http_ok():
            print(f"Ollama started (pid={pid}) and HTTP endpoint responded")
            return pid
        time.sleep(0.5)

    print(f"Started Ollama (pid={pid}) but HTTP endpoint did not respond within {wait_seconds}s")
    return pid


def stop_ollama() -> bool:
    if not PID_FILE.exists():
        print("No PID file found; nothing to stop")
        return False
    try:
        pid = int(PID_FILE.read_text())
    except Exception:
        PID_FILE.unlink(missing_ok=True)
        print("PID file corrupt; removed")
        return False

    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(pid), '/F'], check=False)
        else:
            os.kill(pid, 15)
    except Exception:
        pass
    PID_FILE.unlink(missing_ok=True)
    print(f"Stopped Ollama (pid={pid})")
    return True


def status() -> None:
    ok = is_http_ok()
    print(f"OLLAMA URL: {DEFAULT_URL} -> {'OK' if ok else 'no response'}")
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text())
            print(f"PID file: {PID_FILE} -> pid={pid}")
        except Exception:
            print(f"PID file present but unreadable: {PID_FILE}")


def ensure() -> None:
    if is_http_ok():
        print("Ollama HTTP endpoint already responding")
        return
    print("Ollama not responding; attempting to start...")
    pid = start_ollama()
    if pid:
        print("Start attempted; check status again in a moment.")


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: start|stop|status|ensure")
        return 2
    cmd = argv[0].lower()
    if cmd == 'start':
        start_ollama()
    elif cmd == 'stop':
        stop_ollama()
    elif cmd == 'status':
        status()
    elif cmd == 'ensure':
        ensure()
    else:
        print("Unknown command")
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
