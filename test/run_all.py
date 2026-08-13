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

Progress is checkpointed to .run_all_state.json after every run that produces
an eval_result.json, so an interrupted sweep can be picked up where it stopped
with --resume. A run that died without grading is not checkpointed and is
retried on resume.

--provider/--model are passed straight through to test.py (same meaning and
same defaults there: llama-cpp against the host router unless told otherwise).
Neither is part of the checkpoint's identity, so --resume picks up where the
sweep stopped regardless of which model ran before - pass the same flags on
resume as on the original run.

ANTHROPIC_API_KEY, OPENAI_API_KEY, MODEL and the rest are read from the
gitignored .env at the repo root when they aren't already exported in the
shell (see env_file.py), so a hosted-model sweep needs no key on the command
line.

Usage (from inside test/):
    ./run_all.py
    ./run_all.py --resume
    ./run_all.py --provider anthropic --model claude-opus-5
    ./run_all.py --provider openai --model gpt-5.5
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import env_file

# The repo-root .env (ANTHROPIC_API_KEY, MODEL, ...) - loaded here as well as
# in test.py because this script reads those variables itself (the key check
# below, the startup summary) before spawning anything. The child test.py
# processes inherit what's set here, and loading is idempotent either way.
LOADED_FROM_ENV_FILE = env_file.load_env()

SCRIPT_DIR = Path(__file__).resolve().parent
N_ITERATIONS = 5
TIMEOUT_MINUTES = 60
STATE_FILE = SCRIPT_DIR / ".run_all_state.json"

# Kept in step with test.py's PROVIDERS/HOSTED_PROVIDER_KEYS by hand -
# duplicated rather than imported so this stays a standalone script that only
# shells out to test.py.
HOSTED_PROVIDER_KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
PROVIDERS = ("llama-cpp", *HOSTED_PROVIDER_KEYS)


def log(msg):
    print(f">> {msg}", flush=True)


def discover_tasks():
    return sorted(
        entry.name for entry in SCRIPT_DIR.iterdir()
        if entry.is_dir() and (entry / "task.json").is_file()
    )


def build_plan(tasks):
    """The full sweep, in execution order, as (task, use_skills, iteration) tuples."""
    return [
        (task_name, use_skills, i)
        for task_name in tasks
        for use_skills in (True, False)
        for i in range(1, N_ITERATIONS + 1)
    ]


def save_state(step):
    task_name, use_skills, iteration = step
    STATE_FILE.write_text(json.dumps({
        "last_completed": {"task": task_name, "skills": use_skills, "iteration": iteration},
        "n_iterations": N_ITERATIONS,
    }, indent=2) + "\n")


def resume_index(plan):
    """Index in plan of the first run still to do, per the checkpoint file."""
    if not STATE_FILE.is_file():
        log(f"--resume: no {STATE_FILE.name} found - starting from the beginning.")
        return 0

    state = json.loads(STATE_FILE.read_text())
    last = state.get("last_completed")
    if not last:
        log(f"--resume: {STATE_FILE.name} records no completed run - starting from the beginning.")
        return 0

    if state.get("n_iterations") != N_ITERATIONS:
        log(f"--resume: WARNING - checkpoint was written with N_ITERATIONS={state.get('n_iterations')}, "
            f"now {N_ITERATIONS}; iteration numbering may not line up.")

    step = (last["task"], last["skills"], last["iteration"])
    mode = "skills" if step[1] else "no-skills"
    if step not in plan:
        log(f"--resume: last completed run {step[0]} [{mode}] {step[2]} is not in the current plan "
            f"(task list changed?) - starting from the beginning.")
        return 0

    log(f"--resume: last completed run was {step[0]} [{mode}] {step[2]}/{N_ITERATIONS}.")
    return plan.index(step) + 1


def existing_run_dirs(task_dir):
    runs_dir = task_dir / "runs"
    if not runs_dir.is_dir():
        return set()
    return {p.name for p in runs_dir.iterdir() if p.is_dir()}


def run_one(task_name, use_skills, iteration, total, provider, model):
    """Returns True if the run finished and produced an eval_result.json."""
    task_dir = SCRIPT_DIR / task_name
    before = existing_run_dirs(task_dir)
    mode = "skills" if use_skills else "no-skills"

    log(f"{task_name} [{mode}] {iteration}/{total}: starting (timeout {TIMEOUT_MINUTES}m)...")

    cmd = [sys.executable, str(SCRIPT_DIR / "test.py"), task_name, "--timeout", str(TIMEOUT_MINUTES), "--n", "1"]
    if use_skills:
        cmd.append("--skills")
    if provider:
        cmd += ["--provider", provider]
    if model:
        cmd += ["--model", model]

    start = time.time()
    result = subprocess.run(cmd, cwd=SCRIPT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    duration = int(time.time() - start)

    new_dirs = existing_run_dirs(task_dir) - before
    if len(new_dirs) != 1:
        log(f"{task_name} [{mode}] {iteration}/{total}: WARNING - expected 1 new run dir, found {len(new_dirs)} "
            f"(exit {result.returncode}, {duration}s)")
        return False
    run_dir = task_dir / "runs" / new_dirs.pop()

    eval_file = run_dir / "eval_result.json"
    if not eval_file.is_file():
        log(f"{task_name} [{mode}] {iteration}/{total}: no eval_result.json produced (exit {result.returncode}, {duration}s)")
        return False

    eval_data = json.loads(eval_file.read_text())
    status = "PASS" if eval_data.get("passed") else "FAIL"
    flag = " TIMED_OUT" if eval_data.get("timed_out") else ""
    log(f"{task_name} [{mode}] {iteration}/{total}: {status} score={eval_data.get('score')} ({duration}s){flag}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resume", action="store_true",
                        help=f"continue the sweep after the last run recorded in {STATE_FILE.name}")
    parser.add_argument("--provider", choices=PROVIDERS, default=None,
                        help="pi provider to run every task through (passed to test.py; default: test.py's)")
    parser.add_argument("--model", default=None,
                        help="model id to run every task with (passed to test.py; default: test.py's resolution)")
    args = parser.parse_args()

    if LOADED_FROM_ENV_FILE:
        log(f"Loaded from {env_file.ENV_FILE}: {', '.join(LOADED_FROM_ENV_FILE)}")

    # test.py's own stdout/stderr is suppressed per run, so its die() message
    # would never be seen - check here instead of letting every run fail mute.
    key_var = HOSTED_PROVIDER_KEYS.get(args.provider)
    if key_var and not os.environ.get(key_var):
        log(f"ERROR: {key_var} is not set - required for --provider {args.provider}. "
            f"Export it, or put it in {env_file.ENV_FILE}.")
        sys.exit(1)

    tasks = discover_tasks()
    log(f"Found {len(tasks)} tasks: {', '.join(tasks)}")
    plan = build_plan(tasks)
    log(f"Total runs planned: {len(plan)} ({N_ITERATIONS} with skills + {N_ITERATIONS} without, per task)")
    log(f"Provider: {args.provider or 'test.py default'} | Model: {args.model or os.environ.get('MODEL') or 'test.py default'}")

    start = resume_index(plan) if args.resume else 0
    if start:
        log(f"Resuming at run {start + 1}/{len(plan)} - skipping {start} already-completed run(s).")
    if start >= len(plan):
        log("Nothing left to run.")
        return

    for index, (task_name, use_skills, iteration) in enumerate(plan[start:], start=start + 1):
        log(f"--- run {index}/{len(plan)} ---")
        if run_one(task_name, use_skills, iteration, N_ITERATIONS, args.provider, args.model):
            save_state((task_name, use_skills, iteration))

    log("All runs complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted - stopping.")
        sys.exit(130)
