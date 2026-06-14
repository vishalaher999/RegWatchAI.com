"""
Register RegWatch AI as a Windows scheduled task.

Creates a task named "RegWatch-AI-Daily" that runs run_daily.py
every morning at 7:00 AM using your current Python interpreter.

Run once to set up, or re-run to update the schedule.
Requires no admin privileges (runs as current user).

Usage:
    python scripts/schedule_daily.py              # register at 7:00 AM
    python scripts/schedule_daily.py --time 06:30 # register at 6:30 AM
    python scripts/schedule_daily.py --remove      # delete the task
    python scripts/schedule_daily.py --status      # check if task exists
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TASK_NAME = "RegWatch-AI-Daily"
PYTHON_EXE = sys.executable
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_daily.py"
LOG_PATH = PROJECT_ROOT / "logs" / "scheduler.log"


def task_exists() -> bool:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def register_task(run_time: str = "07:00") -> None:
    """
    Create or replace the scheduled task.
    /F = force (overwrite if exists)
    /SC DAILY = run every day
    /ST = start time (HH:MM)
    /TR = the command to run
    """
    command = f'"{PYTHON_EXE}" "{SCRIPT_PATH}"'

    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", TASK_NAME,
            "/TR", command,
            "/SC", "DAILY",
            "/ST", run_time,
            "/F",   # overwrite if already exists
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"[ok] Task '{TASK_NAME}' scheduled daily at {run_time}")
        print(f"     Python:  {PYTHON_EXE}")
        print(f"     Script:  {SCRIPT_PATH}")
        print(f"     Log:     {LOG_PATH}")
    else:
        print(f"[error] Failed to create task:")
        print(result.stderr or result.stdout)
        sys.exit(1)


def remove_task() -> None:
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"[ok] Task '{TASK_NAME}' removed")
    else:
        print(f"[error] {result.stderr or result.stdout}")
        sys.exit(1)


def show_status() -> None:
    if task_exists():
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
            capture_output=True,
            text=True,
        )
        print(result.stdout)
    else:
        print(f"Task '{TASK_NAME}' does not exist.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage RegWatch AI scheduled task")
    parser.add_argument("--time", default="07:00", help="Run time in HH:MM format (default: 07:00)")
    parser.add_argument("--remove", action="store_true", help="Remove the scheduled task")
    parser.add_argument("--status", action="store_true", help="Show task status")
    args = parser.parse_args()

    if args.remove:
        remove_task()
    elif args.status:
        show_status()
    else:
        register_task(args.time)
