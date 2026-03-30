"""
One-click setup and run utility.

Usage:
    python one_click.py

Default behavior:
  1) Install dependencies from requirements.txt
  2) Start enrichment pipeline in background
  3) Launch monitoring dashboard
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], title: str, check: bool = True, background: bool = False):
    print(f"[ONE-CLICK] {title}: {' '.join(cmd)}")
    if background:
        return subprocess.Popen(cmd)
    return subprocess.run(cmd, check=check)


def main() -> int:
    parser = argparse.ArgumentParser(description="One-click setup for enrichment pipeline")
    parser.add_argument("--skip-install", action="store_true", help="Skip dependency installation")
    parser.add_argument("--dashboard-only", action="store_true", help="Run only dashboard")
    parser.add_argument("--pipeline-only", action="store_true", help="Run only enrichment pipeline")
    args = parser.parse_args()

    root = Path(__file__).parent.resolve()
    requirements = root / "requirements.txt"

    if not args.skip_install:
        _run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            "Upgrading pip",
        )
        _run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
            "Installing project dependencies",
        )

    if args.dashboard_only and args.pipeline_only:
        print("[ONE-CLICK] Use either --dashboard-only or --pipeline-only, not both.")
        return 1

    if args.dashboard_only:
        _run([sys.executable, "-m", "streamlit", "run", "dashboard.py"], "Launching dashboard")
        return 0

    if args.pipeline_only:
        _run([sys.executable, "main.py"], "Starting enrichment pipeline")
        return 0

    _run([sys.executable, "main.py"], "Starting enrichment pipeline (background)", background=True)
    _run([sys.executable, "-m", "streamlit", "run", "dashboard.py"], "Launching monitoring dashboard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
