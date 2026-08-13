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

Every run is given an explicit --run-id (<timestamp>_<s|n><iteration>, e.g.
20260813_213000_s3), so no two runs can land in the same directory or share a
container name even when they start in the same second. Each run's directory
is then read back by that id rather than by diffing runs/ before and after.

--parallel N runs N containers at once (default 1 = the old serial behaviour).
Before fanning out, the shared per-task setup - the GEO download into data/
and the docker build of pytcr-test-<task> - is done once, serially, via
test.py --prepare-only; concurrent runs of one task would otherwise do both at
the same time, racing on the same directory and the same image tag. Note that
N containers each take MEMORY_GB (default 8 GB), and that N only helps when
the model server can actually serve N agents at once: a local llama.cpp router
with `parallel = 1` in its preset serializes them, so --parallel is mostly for
the hosted providers.

Progress is checkpointed to .run_all_state.json after every run that produces
an eval_result.json, so an interrupted sweep can be picked up where it stopped
with --resume. A run that died without grading is not checkpointed and is
retried on resume. The checkpoint records the last run of an unbroken
completed prefix of the plan, which under --parallel is not necessarily the
last run to finish: with runs 3 and 5 done but 4 still going, the checkpoint
stays at 3, so a resume re-runs 4 and 5 rather than skipping 4.

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
    ./run_all.py --provider openai --model gpt-5.5 --parallel 4
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
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
LOCAL_PROVIDER = "llama-cpp"

# Serializes the progress lines. Without it two workers finishing together can
# interleave mid-line, and the sweep's log is the only place a --parallel run's
# progress is visible at all.
LOG_LOCK = threading.Lock()


def log(msg):
    with LOG_LOCK:
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


def step_label(step):
    task_name, use_skills, iteration = step
    return f"{task_name} [{'skills' if use_skills else 'no-skills'}] {iteration}/{N_ITERATIONS}"


def run_id_for(step):
    """A directory/container name unique across concurrent runs: the start
    time plus the step's own identity, which appears exactly once in the plan.
    Two runs starting in the same second therefore still differ."""
    task_name, use_skills, iteration = step
    return f"{datetime.now():%Y%m%d_%H%M%S}_{'s' if use_skills else 'n'}{iteration}"


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
    if step not in plan:
        log(f"--resume: last completed run {step_label(step)} is not in the current plan "
            f"(task list changed?) - starting from the beginning.")
        return 0

    log(f"--resume: last completed run was {step_label(step)}.")
    return plan.index(step) + 1


def prepare_tasks(tasks):
    """Fetches data/ and builds each task's image once, serially, before any
    parallel dispatch. test.py does this itself at the start of every run, but
    N concurrent runs of one task would do it N times at once - two
    fetch_data.py processes writing the same data/ files, and competing
    `docker build -t pytcr-test-<task>` of the same tag."""
    log(f"Preparing {len(tasks)} task(s) serially (data + images) before running in parallel...")
    for task_name in tasks:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "test.py"), task_name, "--prepare-only"],
            cwd=SCRIPT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        )
        if result.returncode != 0:
            log(f"ERROR: preparing {task_name} failed (exit {result.returncode}):\n{result.stderr.strip()}")
            return False
        log(f"  {task_name}: ready")
    return True


def run_one(step, index, total_runs, provider, model):
    """Runs one (task, skill-mode, iteration) to completion.
    Returns True if it produced an eval_result.json."""
    task_name, use_skills, _ = step
    task_dir = SCRIPT_DIR / task_name
    run_id = run_id_for(step)
    label = step_label(step)

    log(f"[{index}/{total_runs}] {label}: starting as {run_id} (timeout {TIMEOUT_MINUTES}m)...")

    cmd = [sys.executable, str(SCRIPT_DIR / "test.py"), task_name,
           "--timeout", str(TIMEOUT_MINUTES), "--n", "1", "--run-id", run_id]
    if use_skills:
        cmd.append("--skills")
    if provider:
        cmd += ["--provider", provider]
    if model:
        cmd += ["--model", model]

    start = time.time()
    result = subprocess.run(cmd, cwd=SCRIPT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    duration = int(time.time() - start)

    # No before/after diff of runs/: with several runs in flight that can't
    # tell which directory is this run's. The id we assigned is the answer.
    run_dir = task_dir / "runs" / run_id
    eval_file = run_dir / "eval_result.json"
    if not eval_file.is_file():
        log(f"[{index}/{total_runs}] {label}: no eval_result.json produced "
            f"(exit {result.returncode}, {duration}s, {run_dir})")
        return False

    eval_data = json.loads(eval_file.read_text())
    status = "PASS" if eval_data.get("passed") else "FAIL"
    flag = " TIMED_OUT" if eval_data.get("timed_out") else ""
    log(f"[{index}/{total_runs}] {label}: {status} score={eval_data.get('score')} ({duration}s){flag}")
    return True


def checkpoint_completed_prefix(plan, completed, next_to_record):
    """Advances the checkpoint over every completed run at the front of the
    plan, stopping at the first one that isn't done. Under --parallel runs
    finish out of order, and recording a later run while an earlier one is
    still in flight would make --resume skip the earlier one."""
    while next_to_record < len(plan) and plan[next_to_record] in completed:
        save_state(plan[next_to_record])
        next_to_record += 1
    return next_to_record


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resume", action="store_true",
                        help=f"continue the sweep after the last run recorded in {STATE_FILE.name}")
    parser.add_argument("--provider", choices=PROVIDERS, default=None,
                        help="pi provider to run every task through (passed to test.py; default: test.py's)")
    parser.add_argument("--model", default=None,
                        help="model id to run every task with (passed to test.py; default: test.py's resolution)")
    parser.add_argument("--parallel", type=int, default=1, metavar="N",
                        help="run N containers at once (default: 1, i.e. one after another)")
    args = parser.parse_args()

    if args.parallel < 1:
        log(f"ERROR: --parallel must be at least 1, got: {args.parallel}")
        sys.exit(1)

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

    if args.parallel > 1:
        memory_gb = os.environ.get("MEMORY_GB", "8")
        log(f"Parallel: {args.parallel} containers at once "
            f"(each capped at MEMORY_GB={memory_gb} GB, so up to {args.parallel}x that in total)")
        if (args.provider or LOCAL_PROVIDER) == LOCAL_PROVIDER:
            log("WARNING: --parallel with the local llama.cpp router - the router serves as many "
                "requests at once as its preset's `parallel` allows (often 1), so the agents will "
                "mostly queue rather than run concurrently.")

    start = resume_index(plan) if args.resume else 0
    if start:
        log(f"Resuming at run {start + 1}/{len(plan)} - skipping {start} already-completed run(s).")
    if start >= len(plan):
        log("Nothing left to run.")
        return

    remaining = plan[start:]
    if args.parallel > 1 and not prepare_tasks(sorted({task for task, _, _ in remaining})):
        sys.exit(1)

    completed = set()
    next_to_record = start
    interrupted = False

    if args.parallel == 1:
        for offset, step in enumerate(remaining):
            if run_one(step, start + offset + 1, len(plan), args.provider, args.model):
                completed.add(step)
                next_to_record = checkpoint_completed_prefix(plan, completed, next_to_record)
    else:
        executor = ThreadPoolExecutor(max_workers=args.parallel)
        futures = {}
        try:
            for offset, step in enumerate(remaining):
                futures[executor.submit(run_one, step, start + offset + 1, len(plan),
                                        args.provider, args.model)] = step
            for future, step in futures.items():
                if future.result():
                    completed.add(step)
                # Checkpointing here (rather than as each run lands) keeps it
                # on this thread; the prefix rule means order doesn't matter.
                next_to_record = checkpoint_completed_prefix(plan, completed, next_to_record)
        except KeyboardInterrupt:
            # Queued-but-not-started runs are dropped; the ones already running
            # get the same SIGINT from the terminal that a serial run would, so
            # test.py stops their containers and grades what exists.
            interrupted = True
            log("Interrupted - cancelling queued runs and waiting for the running ones to stop...")
            executor.shutdown(wait=True, cancel_futures=True)
        else:
            executor.shutdown(wait=True)

    if interrupted:
        log(f"Stopped after {len(completed)} completed run(s).")
        sys.exit(130)

    log(f"All runs complete ({len(completed)}/{len(remaining)} produced a result).")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted - stopping.")
        sys.exit(130)
