#!/usr/bin/env python3
"""Runs every task directory's eval suite n times with skills and n times without,
each run capped at a 1-hour timeout.

Wraps test.py per (task, skill-mode, iteration) with its stdout/stderr
suppressed - test.py itself prints the model's raw output (thinking, tool
calls, text) interleaved with its own progress, and there's no flag to
separate the two. Progress is instead reported here from each run's
eval_result.json once it lands; the model's full output is still written
to disk as usual under <task>/runs/<run_id>/run.txt and run.jsonl - just
not echoed to this terminal.

Usage (from inside test/):
    ./run_all.pyuvy
"""
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
N_ITERATIONS = 5
TIMEOUT_MINUTES = 60


def log(msg):
    print(f">> {msg}", flush=True)


def discover_tasks():
    return sorted(
        entry.name for entry in SCRIPT_DIR.iterdir()
        if entry.is_dir() and (entry / "task.json").is_file()
    )


def existing_run_dirs(task_dir):
    runs_dir = task_dir / "runs"
    if not runs_dir.is_dir():
        return set()
    return {p.name for p in runs_dir.iterdir() if p.is_dir()}


def run_one(task_name, use_skills, iteration, total):
    task_dir = SCRIPT_DIR / task_name
    before = existing_run_dirs(task_dir)
    mode = "skills" if use_skills else "no-skills"

    log(f"{task_name} [{mode}] {iteration}/{total}: starting (timeout {TIMEOUT_MINUTES}m)...")

    cmd = [sys.executable, str(SCRIPT_DIR / "test.py"), task_name, "--timeout", str(TIMEOUT_MINUTES), "--n", "1"]
    if use_skills:
        cmd.append("--skills")

    start = time.time()
    result = subprocess.run(cmd, cwd=SCRIPT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    duration = int(time.time() - start)

    new_dirs = existing_run_dirs(task_dir) - before
    if len(new_dirs) != 1:
        log(f"{task_name} [{mode}] {iteration}/{total}: WARNING - expected 1 new run dir, found {len(new_dirs)} "
            f"(exit {result.returncode}, {duration}s)")
        return
    run_dir = task_dir / "runs" / new_dirs.pop()

    eval_file = run_dir / "eval_result.json"
    if not eval_file.is_file():
        log(f"{task_name} [{mode}] {iteration}/{total}: no eval_result.json produced (exit {result.returncode}, {duration}s)")
        return

    eval_data = json.loads(eval_file.read_text())
    status = "PASS" if eval_data.get("passed") else "FAIL"
    flag = " TIMED_OUT" if eval_data.get("timed_out") else ""
    log(f"{task_name} [{mode}] {iteration}/{total}: {status} score={eval_data.get('score')} ({duration}s){flag}")


def main():
    tasks = discover_tasks()
    log(f"Found {len(tasks)} tasks: {', '.join(tasks)}")
    total_runs = len(tasks) * 2 * N_ITERATIONS
    log(f"Total runs planned: {total_runs} ({N_ITERATIONS} with skills + {N_ITERATIONS} without, per task)")

    for task_name in tasks:
        for use_skills in (True, False):
            for i in range(1, N_ITERATIONS + 1):
                run_one(task_name, use_skills, i, N_ITERATIONS)

    log("All runs complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted - stopping.")
        sys.exit(130)
