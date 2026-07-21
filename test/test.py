#!/usr/bin/env python3
"""Runs one task directory's evaluation inside an isolated container.

Usage (from inside test/):
    ./test.py <task-dir-name> [--skills] [--timeout MINUTES] [--n COUNT]
    MODEL=host/qwen3.5 ./test.py 01-data-loading --skills

--skills: bind-mounts the project's skills/ (read-only) into the container
    at /root/.claude/skills, opencode's "external skills (auto-loaded)"
    location. Sourced from skills/, not .claude/skills/ (gitignored
    symlink, absent on a fresh clone).

--timeout MINUTES: kill the agent's container if it hasn't finished within
    this many minutes (default: 20). A background thread issues
    `docker stop` on the run's container, which (started with --rm) also
    removes it; whatever task.ipynb/output.json the agent had written by
    then is still extracted as usual.

--n COUNT: repeat the run COUNT times (default: 1), each stored as its own
    run directory under <task-dir>/runs/.

Ctrl-C (or a TERM) stops the in-flight container the same way a timeout
does - extracts/grades whatever task.ipynb/output.json exists, marks
eval_result.json with interrupted: true, skips any remaining --n
iterations, and exits with status 130.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DOCKERFILE_TEMPLATE = """ARG BASE_IMAGE=pytcr-agent:latest
FROM ${BASE_IMAGE}

# Miniforge (conda + mamba, conda-forge-first): mamba resolves the
# bioconda/conda-forge scanpy+scirpy stack far faster and more reliably
# than the classic conda solver. gzip: task data ships as .csv.gz/.mtx.gz -
# guaranteed here rather than left to whatever the base image happens to
# bundle, so the agent never has to install it itself mid-task.
RUN apt-get update \\
    && apt-get install -y --no-install-recommends wget bzip2 gzip ca-certificates \\
    && rm -rf /var/lib/apt/lists/* \\
    && wget -qO /tmp/miniforge.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-$(uname -m).sh" \\
    && bash /tmp/miniforge.sh -b -p /opt/conda \\
    && rm /tmp/miniforge.sh

# environment.yml lives at test/environment.yml, one level up from this
# task directory - the build context is test/ (see `docker build -f`
# below), so it's visible here as a context-root file.
COPY environment.yml /tmp/environment.yml
RUN /opt/conda/bin/mamba env create -f /tmp/environment.yml \\
    && /opt/conda/bin/conda clean -afy

# Make the task's conda env (name: pytcr, from environment.yml) the
# default on PATH for every process in the container, including the
# bash/python calls opencode's agent makes - no `conda activate` needed.
ENV PATH=/opt/conda/envs/pytcr/bin:$PATH
"""


def log(msg):
    print(f">> {msg}")


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, **kwargs):
    return subprocess.run(cmd, **kwargs)


class QuietArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise SystemExit(2)


def parse_args():
    usage = (
        "Usage: test.py <task-dir-name> [--skills] [--timeout MINUTES] [--n COUNT]  "
        "(run from inside test/, e.g. ./test.py 01-data-loading --skills)"
    )
    parser = QuietArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    parser.add_argument("task_name", nargs="?")
    parser.add_argument("--skills", action="store_true")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--n", type=int, default=1)
    try:
        args = parser.parse_args()
    except SystemExit:
        die(usage)
    if not args.task_name:
        die(usage)
    if args.timeout <= 0:
        die(f"--timeout must be a positive integer (minutes), got: {args.timeout}")
    if args.n <= 0:
        die(f"--n must be a positive integer, got: {args.n}")
    return args


def check_docker():
    if shutil.which("docker") is None:
        die("Docker isn't installed.")
    if run(["docker", "info"], capture_output=True).returncode != 0:
        die("Docker daemon isn't running (open Docker Desktop and retry).")


def ensure_base_image():
    if run(["docker", "image", "inspect", "pytcr-agent:latest"], capture_output=True).returncode != 0:
        log("Building base agent image from docker-agent/...")
        run(["docker", "build", "-t", "pytcr-agent:latest", str(REPO_ROOT / "docker-agent")], check=True)


def ensure_task_dockerfile(task_dir):
    dockerfile = task_dir / "Dockerfile"
    if dockerfile.exists():
        log(f"Using existing {dockerfile}")
    else:
        log(f"Generating {dockerfile}")
        dockerfile.write_text(DOCKERFILE_TEMPLATE)
    return dockerfile


def render_prompt(task_json):
    result = run(
        [sys.executable, str(SCRIPT_DIR / "render_prompt.py"), str(task_json), str(SCRIPT_DIR / "SYSTEM.md")],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def format_event(event):
    etype = event.get("type")
    part = event.get("part", {})
    if etype == "reasoning":
        return f"🧠 THINKING: {part.get('text', '')}"
    if etype == "tool_use":
        state = part.get("state", {})
        input_str = json.dumps(state.get("input"))[:200]
        output_str = str(state.get("output", ""))[:300]
        return f"🔧 TOOL: {part.get('tool', '')}\n   IN:  {input_str}\n   OUT: {output_str}"
    if etype == "text":
        return f"💬 OUTPUT:\n{part.get('text', '')}"
    if etype == "step_finish":
        tokens = part.get("tokens", {})
        return (
            f"📊 STEP TOKENS: input={tokens.get('input')} output={tokens.get('output')} "
            f"reasoning={tokens.get('reasoning')} total={tokens.get('total')}"
        )
    return None


def timeout_watchdog(container_name, timeout_seconds, timed_out_event):
    time.sleep(timeout_seconds)
    still_running = run(
        ["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True,
    ).stdout.splitlines()
    if container_name in still_running:
        timed_out_event.set()
        print(f"TIMEOUT: no result within {timeout_seconds // 60}m, stopping {container_name}", file=sys.stderr)
        run(["docker", "stop", container_name], capture_output=True)


def stream_docker_run(cmd, log_file, pretty_file, container_name):
    interrupted = False
    with open(log_file, "w") as jsonl_f, open(pretty_file, "a") as pretty_f:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            for line in proc.stdout:
                jsonl_f.write(line)
                jsonl_f.flush()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                formatted = format_event(event)
                if formatted is not None:
                    print(formatted)
                    pretty_f.write(formatted + "\n")
                    pretty_f.flush()
        except KeyboardInterrupt:
            # The terminal delivers SIGINT to the docker run child directly
            # too (same foreground process group), so this stop is mostly a
            # backstop - but it's what makes the run reliably terminate even
            # if that direct delivery doesn't land right.
            interrupted = True
            print(f"\nInterrupted - stopping {container_name} and extracting whatever outputs exist...", file=sys.stderr)
            run(["docker", "stop", container_name], capture_output=True)
        proc.wait()
        return proc.returncode, interrupted


def run_once(task_name, task_dir, task_image, prompt, model, memory_gb, use_skills, timeout_min, iter_num, n):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    if n > 1:
        run_id = f"{run_id}_{iter_num}"
    run_dir = task_dir / "runs" / run_id
    (run_dir / "workspace").mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(prompt)

    container_name = f"pytcr-test-{task_name}-{run_id}"
    log(f"Starting container: {container_name} (model: {model}, timeout: {timeout_min}m)")
    log(f"Workspace: {run_dir / 'workspace'}")

    log_file = run_dir / "run.jsonl"
    pretty_file = run_dir / "run.txt"

    header = (
        f"=== Task: {task_name} ===\n"
        f"=== Model: {model} ===\n"
        f"=== Skills: {'enabled (' + str(REPO_ROOT / 'skills') + ')' if use_skills else 'disabled'} ===\n"
        f"=== Timeout: {timeout_min}m ===\n"
        f"=== Prompt: ===\n"
        f"{prompt}\n"
    )
    print(header)
    pretty_file.write_text(header)

    skills_mount = []
    if use_skills:
        skills_mount = ["-v", f"{REPO_ROOT / 'skills'}:/root/.claude/skills:ro"]

    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--add-host=host.docker.internal:host-gateway",
        "--cap-drop=ALL", "--security-opt", "no-new-privileges:true",
        "--memory", f"{memory_gb}g",
        "-v", f"{run_dir / 'workspace'}:/root/task",
        "-v", f"{task_dir / 'data'}:/root/task/data:ro",
        *skills_mount,
        "-w", "/root/task",
        task_image,
        "opencode", "run", "--model", model, "--format", "json", "--thinking",
        "--dangerously-skip-permissions", prompt,
    ]

    timed_out_event = threading.Event()
    watchdog = threading.Thread(
        target=timeout_watchdog, args=(container_name, timeout_min * 60, timed_out_event), daemon=True,
    )
    watchdog.start()

    start_time = time.time()
    run_status, interrupted = stream_docker_run(docker_cmd, log_file, pretty_file, container_name)
    if interrupted:
        run_status = 130
    duration_s = int(time.time() - start_time)

    timed_out = timed_out_event.is_set()

    with open(pretty_file, "a") as f:
        f.write("\n")
        if timed_out:
            f.write(f"=== TIMED OUT after {timeout_min}m ===\n")
        if interrupted:
            f.write("=== INTERRUPTED by user ===\n")
        f.write(f"=== Container exit status: {run_status} ===\n")
        f.write(f"=== Duration: {duration_s}s ===\n")

    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    for fname in ("task.ipynb", "output.json"):
        src = run_dir / "workspace" / fname
        if src.exists():
            shutil.copy(src, outputs_dir / fname)
        else:
            msg = f"WARNING: {fname} was not produced"
            print(msg)
            with open(pretty_file, "a") as f:
                f.write(msg + "\n")
    shutil.rmtree(run_dir / "workspace")
    (run_dir / "workspace").mkdir()

    eval_file = run_dir / "eval_result.json"
    grade_result = run(
        [sys.executable, str(SCRIPT_DIR / "grade.py"), str(task_dir / "task.json"),
         str(outputs_dir / "output.json"), str(duration_s), "1" if use_skills else "0"],
        capture_output=True, text=True, check=True,
    )
    eval_data = json.loads(grade_result.stdout)
    eval_data["timed_out"] = timed_out
    eval_data["interrupted"] = interrupted
    eval_file.write_text(json.dumps(eval_data, indent=2))

    eval_block = f"=== Evaluation ===\n{eval_file.read_text()}\n"
    print(eval_block)
    with open(pretty_file, "a") as f:
        f.write(eval_block)

    log(f"Run {iter_num}/{n} done.")
    log(f"Logs:    {log_file} / {pretty_file}")
    log(f"Outputs: {outputs_dir}")
    log(f"Eval:    {eval_file}")

    return (1 if timed_out else run_status), interrupted


def main():
    args = parse_args()
    model = os.environ.get("MODEL", "host/glm-4.7-flash-128k")
    memory_gb = os.environ.get("MEMORY_GB", "8")

    task_dir = SCRIPT_DIR / args.task_name
    if args.skills and not (REPO_ROOT / "skills").exists():
        die(f"--skills was passed but {REPO_ROOT / 'skills'} doesn't exist")
    if not task_dir.is_dir():
        die(f"No such task directory: {task_dir}")
    task_json = task_dir / "task.json"
    if not task_json.is_file():
        die(f"Missing task.json in {task_dir}")
    if not (task_dir / "data").is_dir():
        die(f"Missing data/ in {task_dir}")
    try:
        json.loads(task_json.read_text())
    except json.JSONDecodeError:
        die(f"task.json in {task_dir} is not valid JSON")

    check_docker()
    ensure_base_image()
    ensure_task_dockerfile(task_dir)

    task_image = f"pytcr-test-{args.task_name}"
    log(f"Building task image: {task_image}")
    run(["docker", "build", "-f", str(task_dir / "Dockerfile"), "-t", task_image, str(SCRIPT_DIR)], check=True)

    prompt = render_prompt(task_json)

    statuses = []
    for i in range(1, args.n + 1):
        if args.n > 1:
            log(f"=== Run {i}/{args.n} ===")
        status, interrupted = run_once(
            args.task_name, task_dir, task_image, prompt, model, memory_gb,
            args.skills, args.timeout, i, args.n,
        )
        statuses.append(status)
        if interrupted:
            log("Stopping - no further runs will be started.")
            sys.exit(130)

    overall_status = 0 if all(s == 0 for s in statuses) else 1
    if args.n > 1:
        log(f"All {args.n} runs done. Statuses: {statuses}")

    sys.exit(overall_status)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
