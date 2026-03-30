"""
Helpers for controlling the enrichment pipeline process.
Used by the Streamlit dashboard and terminal checks.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from enrichment import config


def read_pid() -> int | None:
    if not config.PIPELINE_PID_FILE.exists():
        return None
    try:
        raw = config.PIPELINE_PID_FILE.read_text(encoding="utf-8").strip()
        return int(raw) if raw else None
    except Exception:
        return None


def write_pid(pid: int) -> None:
    config.PIPELINE_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.PIPELINE_PID_FILE.write_text(str(pid), encoding="utf-8")


def clear_pid() -> None:
    try:
        if config.PIPELINE_PID_FILE.exists():
            config.PIPELINE_PID_FILE.unlink()
    except Exception:
        pass


def is_pid_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in (result.stdout or "")
    except Exception:
        return False


def start_pipeline() -> tuple[bool, str]:
    current_pid = read_pid()
    if is_pid_running(current_pid):
        return False, f"Pipeline already running (PID {current_pid})."

    log_path = config.PIPELINE_RUNTIME_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=log_file,
            stderr=log_file,
            cwd=Path(__file__).resolve().parents[1],
        )

    write_pid(proc.pid)
    return True, f"Pipeline started (PID {proc.pid})."


def stop_pipeline() -> tuple[bool, str]:
    pid = read_pid()
    if not pid:
        return False, "No tracked pipeline process found."
    if not is_pid_running(pid):
        clear_pid()
        return False, "Tracked pipeline is not running."

    try:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        clear_pid()
        if result.returncode == 0:
            return True, f"Pipeline stopped (PID {pid})."
        err = (result.stderr or result.stdout or "Unknown stop error").strip()
        return False, f"Stop command failed: {err[:200]}"
    except Exception as exc:
        return False, f"Stop failed: {str(exc)[:200]}"
