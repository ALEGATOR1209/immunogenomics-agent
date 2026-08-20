#!/usr/bin/env python3
"""Runs one task directory's evaluation inside an isolated container.

Usage (from inside test/):
    ./test.py <task-dir-name> [--skills] [--timeout MINUTES] [--n COUNT] [--provider PROVIDER] [--model MODEL]
    MODEL='unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL' ./test.py 01-data-loading --skills
    ./test.py 01-data-loading --model 'ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M'
    ./test.py 01-data-loading --provider anthropic --model claude-opus-5
    ./test.py 01-data-loading --provider openai --model gpt-5.5

--provider PROVIDER: which pi provider to run the agent through - "llama-cpp"
    (default) for the host's local llama.cpp router, or one of the hosted
    APIs, "anthropic" and "openai" (both pi built-ins - no extra package
    needed, unlike llama-cpp's pi-llama). A hosted provider requires its API
    key on the host (ANTHROPIC_API_KEY / OPENAI_API_KEY); only that one key is
    passed into the container, never baked into the image. Model resolution
    differs by provider - see --model below.

--model MODEL: which model id to run.
    llama-cpp: the id as the router reports it. Precedence: this flag, then
    the MODEL env var, then - if exactly one model is loaded on the router -
    that one. The router only serves loaded models, so there's no useful
    hardcoded default; list them with ../docker-agent/llama-server.sh --list.
    anthropic/openai: a literal API model id (claude-opus-5, gpt-5.5, ...).
    Precedence: this flag, then MODEL. No router to fall back to - required
    outright since any hardcoded default would be wrong most of the time.
    Nothing here validates the id against a list: pi forwards it to the
    provider's API as given, so a model newer than pi's own bundled catalog
    works without any change to pi or to this script.

Environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, MODEL, MEMORY_GB,
LLAMA_BASE_URL, HOST_LLAMA_URL) are also read from the gitignored .env at the
repo root, if one exists - anything already exported in the shell takes
precedence over it.

--skills: bind-mounts the project's skills/ (read-only) into the container
    at /root/.pi/agent/skills, pi's global auto-discovered skills location
    (docs/skills.md). Sourced from skills/, not .claude/skills/ (gitignored
    symlink, absent on a fresh clone).

The model server is llama.cpp's router running natively on the host; the
container reaches it via host.docker.internal. Start it with
../docker-agent/llama-server.sh (which binds 0.0.0.0 - a router on
127.0.0.1 is invisible to the container). Override the URL with
LLAMA_BASE_URL. None of this applies to the hosted providers, which talk
directly to api.anthropic.com / api.openai.com over the container's normal
internet egress (the container isn't network-isolated - see
docker-agent/README.md).

--timeout MINUTES: kill the agent's container if it hasn't finished within
    this many minutes (default: 20). A background thread issues
    `docker stop` on the run's container, which (started with --rm) also
    removes it; whatever task.ipynb/output.json the agent had written by
    then is still extracted as usual.

--n COUNT: repeat the run COUNT times (default: 1), each stored as its own
    run directory under <task-dir>/runs/.

--run-id ID: name the run directory (and the container) ID instead of the
    usual start timestamp. Timestamps are only unique per process - two
    test.py processes starting the same task in the same second would land in
    one directory and fight over it - so run_all.py --parallel assigns each
    run an explicit id. Letters, digits, '.', '_' and '-' only; incompatible
    with --n > 1, which would reuse the one id for every iteration.

--prepare-only: fetch data/ and build the images for the task, then exit
    without starting an agent. Needs no model and no API key. This is the
    shared setup that several concurrent runs of one task would otherwise do
    at the same time - a duplicated GEO download into the same data/ and
    competing builds of the same image tag - so run_all.py --parallel does it
    once, serially, before fanning out.

Ctrl-C (or a TERM) stops the in-flight container the same way a timeout
does - extracts/grades whatever task.ipynb/output.json exists, marks
eval_result.json with interrupted: true, skips any remaining --n
iterations, and exits with status 130.

Optional <task-dir>/starter.ipynb: if present, copied into the writable
workspace as task.ipynb before the container starts, so the agent begins
from a partially-built notebook instead of an empty one - for tasks scoped
to one pipeline stage that assume an earlier stage's setup already happened.
Keep it out of data/ (that mount is read-only, so the agent would have to
discover and copy it out itself before being able to edit it - exactly the
kind of read-only-filesystem confusion this is meant to avoid).

If <task-dir>/data/ doesn't exist yet and task.json has a "data" field
(e.g. {"type": "GEO", "uri": "GSM4339771"}, or a list of those for several
samples), it's fetched automatically via fetch_data.py before the build.
Run that script directly (`./fetch_data.py <task-dir>`) to pre-fetch without
starting a run.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import env_file

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

# Before anything reads os.environ below: the repo-root .env supplies
# ANTHROPIC_API_KEY/MODEL/MEMORY_GB/LLAMA_BASE_URL etc. when they aren't
# already exported. Anything actually exported in the shell still wins.
LOADED_FROM_ENV_FILE = env_file.load_env()

# Where the container reaches the host's llama.cpp router, and where this
# script (running on the host) reaches the same server to resolve model ids.
CONTAINER_LLAMA_URL = os.environ.get("LLAMA_BASE_URL", "http://host.docker.internal:8080")
HOST_LLAMA_URL = os.environ.get("HOST_LLAMA_URL", "http://127.0.0.1:8080")

# The provider id registered by git:github.com/huggingface/pi-llama, which
# docker-agent's Dockerfile installs. Note the hyphen: pi also ships a
# separate built-in "llama.cpp" (dot) provider, which is NOT this one.
LLAMA_CPP_PROVIDER = "llama-cpp"

# pi's built-in hosted providers - already present in pi-coding-agent's own
# dependencies, unlike llama-cpp which needs the separate pi-llama package.
# Each maps to the one env var pi reads its credential from, which is also
# the only thing this script forwards into the container for it.
ANTHROPIC_PROVIDER = "anthropic"
OPENAI_PROVIDER = "openai"

HOSTED_PROVIDER_KEYS = {
    ANTHROPIC_PROVIDER: "ANTHROPIC_API_KEY",
    OPENAI_PROVIDER: "OPENAI_API_KEY",
}

# An example id per hosted provider, used only in the "you must pass --model"
# error. Not a default and not a whitelist: pi forwards whatever id it's given
# to the provider's API, including ones its own bundled model catalog predates
# (claude-opus-5 ran fine under pi 0.83.0, whose catalog stops at
# claude-opus-4-8), so newer models need no change here.
HOSTED_PROVIDER_EXAMPLES = {
    ANTHROPIC_PROVIDER: "claude-opus-5",
    OPENAI_PROVIDER: "gpt-5.5",
}

PROVIDERS = (LLAMA_CPP_PROVIDER, *HOSTED_PROVIDER_KEYS)

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
# channel_priority flexible: strict (Miniforge's default) refuses to mix
# bioconda's scirpy>=0.24 with conda-forge's anndata>=0.9 it depends on,
# even though both are installable together - see the solver's own
# "Could not solve for environment specs" error without this.
COPY environment.yml /tmp/environment.yml
RUN /opt/conda/bin/conda config --set channel_priority flexible \\
    && /opt/conda/bin/mamba env create -f /tmp/environment.yml \\
    && /opt/conda/bin/conda clean -afy

# Make the task's conda env (name: pytcr, from environment.yml) the
# default on PATH for every process in the container, including the
# bash/python calls pi's agent makes - no `conda activate` needed.
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
        "Usage: test.py <task-dir-name> [--skills] [--timeout MINUTES] [--n COUNT] "
        "[--provider {llama-cpp,anthropic,openai}] [--model MODEL] [--run-id ID] [--prepare-only]  "
        "(run from inside test/, e.g. ./test.py 01-data-loading --skills)"
    )
    parser = QuietArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    parser.add_argument("task_name", nargs="?")
    parser.add_argument("--skills", action="store_true")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--provider", type=str, choices=PROVIDERS, default=LLAMA_CPP_PROVIDER)
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--run-id", dest="run_id", type=str, default=None)
    parser.add_argument("--prepare-only", action="store_true")
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
    if args.run_id is not None:
        # The id becomes a directory name under runs/ and part of the
        # container name, so keep it to characters that are safe in both.
        if not re.fullmatch(r"[A-Za-z0-9._-]+", args.run_id):
            die(f"--run-id may only contain letters, digits, '.', '_' and '-', got: {args.run_id}")
        if args.n > 1:
            die("--run-id can't be combined with --n > 1 - every iteration would reuse the same directory.")
    return args


def router_models():
    """Every model the host's llama.cpp router knows, as (id, status) pairs.
    Returns None when the router isn't reachable, so callers can tell "no
    server" apart from "server with nothing loaded"."""
    try:
        with urllib.request.urlopen(f"{HOST_LLAMA_URL}/models", timeout=5) as resp:
            data = json.loads(resp.read())
        return [(m["id"], m["status"]["value"]) for m in data["data"]]
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return None


def get_model_server(provider):
    """What eval_result.json records as having served the model. The router
    reports no version of its own, so for llama-cpp this is the server kind
    plus whether it was actually reachable at run time; the hosted providers
    talk straight to their own API, so there's no local reachability to check
    and the provider id is the whole answer."""
    if provider in HOSTED_PROVIDER_KEYS:
        return provider
    return "llama.cpp" if router_models() is not None else "llama.cpp (unreachable)"


def resolve_model(explicit, provider):
    """--model, else MODEL, else - for llama-cpp only - the single loaded
    model on the router.

    There is deliberately no hardcoded default: for llama-cpp the router
    serves only models that are currently loaded, so any fixed id would be
    wrong most of the time; for the hosted providers there's no router to
    fall back to at all. Failing loudly here beats a run that dies inside the
    container with an opaque error."""
    if explicit:
        return explicit
    if os.environ.get("MODEL"):
        return os.environ["MODEL"]

    if provider in HOSTED_PROVIDER_KEYS:
        die(
            f"No --model/MODEL given for --provider {provider}.\n"
            f"  Pass a model id, e.g. --model {HOSTED_PROVIDER_EXAMPLES[provider]}"
        )

    models = router_models()
    if models is None:
        die(
            f"No llama.cpp router answering at {HOST_LLAMA_URL}, and no --model/MODEL given.\n"
            "  Start one:  ../docker-agent/llama-server.sh --load <model-id>"
        )
    loaded = [mid for mid, status in models if status == "loaded"]
    if not loaded:
        known = "\n".join(f"    {mid}" for mid, _ in models) or "    (none)"
        die(
            "The router has no model loaded, and no --model/MODEL was given.\n"
            f"  Load one:  ../docker-agent/llama-server.sh --load <model-id>\n"
            f"  Known models:\n{known}"
        )
    if len(loaded) > 1:
        opts = "\n".join(f"    {mid}" for mid in loaded)
        die(f"Several models are loaded - pass --model to pick one:\n{opts}")
    log(f"Using the router's only loaded model: {loaded[0]}")
    return loaded[0]


def check_docker():
    if shutil.which("docker") is None:
        die("Docker isn't installed.")
    if run(["docker", "info"], capture_output=True).returncode != 0:
        die("Docker daemon isn't running (open Docker Desktop and retry).")


def ensure_base_image():
    if run(["docker", "image", "inspect", "pytcr-agent:latest"], capture_output=True).returncode != 0:
        log("Building base agent image from docker-agent/...")
        run(["docker", "build", "-t", "pytcr-agent:latest", str(REPO_ROOT / "docker-agent")], check=True)


def declared_data_targets(task_config):
    """The data/ subfolders task.json says should exist, as a set of names.

    fetch_data.py puts each entry in data/<path> when "path" is given and
    data/<uri> otherwise, so those are exactly the folders to look for.
    """
    entries = task_config.get("data") or []
    if isinstance(entries, dict):
        entries = [entries]
    return {e.get("path") or e.get("uri") for e in entries if e.get("path") or e.get("uri")}


def ensure_task_data(task_dir, task_config):
    """Downloads data/ via fetch_data.py if task.json declares a "data"
    source and the declared folders aren't there yet. Runs before the Docker
    build so a fresh clone (data/ gitignored) can go straight to
    `./test.py <task>` for tasks that declare a source, without a separate
    manual step first.

    Checks the *declared* folders rather than "is data/ non-empty": task 08
    ships data/metadata.csv in git, which made data/ look populated, so the
    fetch was skipped and the agent spent its whole run exploring a directory
    holding one 275-byte CSV and none of the 24 GEO samples.
    """
    data_dir = task_dir / "data"
    wanted = declared_data_targets(task_config)
    if wanted:
        if data_dir.is_dir() and all((data_dir / name).exists() for name in wanted):
            return
    elif data_dir.is_dir() and any(data_dir.iterdir()):
        return
    if not task_config.get("data"):
        die(f"Missing data/ in {task_dir} (and task.json has no \"data\" field to fetch it automatically).")
    log(f"data/ missing for {task_dir.name} - fetching via fetch_data.py...")
    run([sys.executable, str(SCRIPT_DIR / "fetch_data.py"), str(task_dir)], check=True)


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


def _part_text(part):
    """pi's content parts keep their payload under a type-named key ("text"
    for text, "thinking" for thinking); tolerate either, plus older shapes."""
    for key in ("text", "thinking", "content"):
        value = part.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _brief(value, limit):
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


def format_event(event):
    """Renders pi's --mode json event stream (docs/json.md) into the readable
    run.txt. Only the events worth reading are rendered; the untouched stream
    is always kept alongside it in run.jsonl, so anything skipped here is
    still recoverable.

    Deliberately ignores message_update: those carry per-token deltas, and
    echoing them would reproduce the whole response one fragment at a time.
    The completed message arrives in message_end."""
    etype = event.get("type")

    if etype == "message_end":
        message = event.get("message", {})
        if message.get("role") != "assistant":
            return None
        lines = []
        for part in message.get("content", []) or []:
            ptype = part.get("type")
            body = _part_text(part)
            if ptype == "thinking" and body:
                lines.append(f"🧠 THINKING: {body}")
            elif ptype == "text" and body:
                lines.append(f"💬 OUTPUT:\n{body}")
        usage = message.get("usage") or {}
        if usage:
            summary = " ".join(f"{k}={v}" for k, v in usage.items() if isinstance(v, (int, float)))
            if summary:
                lines.append(f"📊 TOKENS: {summary}")
        stop = message.get("stopReason")
        # The opencode-era failure mode was a turn ending with no tool call
        # and nothing left to do; surfacing stopReason keeps that visible.
        if stop and stop not in ("stop", "toolUse"):
            lines.append(f"⚠️  STOP REASON: {stop} {message.get('errorMessage', '')}".rstrip())
        return "\n".join(lines) if lines else None

    if etype == "tool_execution_start":
        return f"🔧 TOOL: {event.get('toolName', '')}\n   IN:  {_brief(event.get('args'), 200)}"

    if etype == "tool_execution_end":
        marker = "ERR" if event.get("isError") else "OUT"
        return f"   {marker}: {_brief(event.get('result'), 300)}"

    if etype == "compaction_start":
        return f"🗜️  COMPACTION START ({event.get('reason')})"

    if etype == "compaction_end":
        return f"🗜️  COMPACTION END ({event.get('reason')}) aborted={event.get('aborted')}"

    if etype == "auto_retry_start":
        return (
            f"🔁 RETRY {event.get('attempt')}/{event.get('maxAttempts')} "
            f"after: {_brief(event.get('errorMessage'), 200)}"
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


def run_once(task_name, task_dir, task_image, prompt, model, model_server, provider, memory_gb, use_skills, timeout_min, iter_num, n, run_id=None):
    start_dt = datetime.now()
    if run_id is None:
        # A timestamp to the second is unique enough for runs started from
        # this process, but not across concurrent test.py processes - which
        # is why run_all.py's --parallel passes an explicit --run-id instead.
        run_id = start_dt.strftime("%Y%m%d_%H%M%S")
        if n > 1:
            run_id = f"{run_id}_{iter_num}"
    run_dir = task_dir / "runs" / run_id
    (run_dir / "workspace").mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(prompt)

    starter_notebook = task_dir / "starter.ipynb"
    if starter_notebook.exists():
        shutil.copy(starter_notebook, run_dir / "workspace" / "task.ipynb")
        log(f"Pre-seeded task.ipynb from {starter_notebook}")

    container_name = f"pytcr-test-{task_name}-{run_id}"
    log(f"Starting container: {container_name} (model: {model}, timeout: {timeout_min}m)")
    log(f"Workspace: {run_dir / 'workspace'}")

    log_file = run_dir / "run.jsonl"
    pretty_file = run_dir / "run.txt"

    header = (
        f"=== Task: {task_name} ===\n"
        f"=== Start: {start_dt.isoformat()} ===\n"
        f"=== Model: {model} ===\n"
        f"=== Harness: pi ===\n"
        f"=== Model server: {model_server} ===\n"
        f"=== Skills: {'enabled (' + str(REPO_ROOT / 'skills') + ')' if use_skills else 'disabled'} ===\n"
        f"=== Timeout: {timeout_min}m ===\n"
        f"=== Prompt: ===\n"
        f"{prompt}\n"
    )
    print(header)
    pretty_file.write_text(header)

    skills_mount = []
    if use_skills:
        # pi auto-discovers skills in ~/.pi/agent/skills (docs/skills.md,
        # "Global"), so mounting there needs no --skill flag - the same
        # arrangement the opencode setup had with ~/.claude/skills.
        skills_mount = ["-v", f"{REPO_ROOT / 'skills'}:/root/.pi/agent/skills:ro"]

    # Exactly one of these is ever passed in: LLAMA_BASE_URL for the local
    # router, or the one API key belonging to the hosted provider in use - so
    # a llama-cpp run's container never sees a stray API key, and an openai
    # run never sees the Anthropic key or vice versa.
    if provider in HOSTED_PROVIDER_KEYS:
        key_var = HOSTED_PROVIDER_KEYS[provider]
        provider_env = ["-e", f"{key_var}={os.environ[key_var]}"]
    else:
        provider_env = ["-e", f"LLAMA_BASE_URL={CONTAINER_LLAMA_URL}"]

    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--add-host=host.docker.internal:host-gateway",
        "--cap-drop=ALL", "--security-opt", "no-new-privileges:true",
        "--memory", f"{memory_gb}g",
        *provider_env,
        "-v", f"{run_dir / 'workspace'}:/root/task",
        "-v", f"{task_dir / 'data'}:/root/task/data:ro",
        *skills_mount,
        "-w", "/root/task",
        task_image,
        # pi has no permission prompts to bypass (no built-in sandbox - see
        # its docs/security.md), so unlike opencode there's no
        # --dangerously-skip-permissions equivalent to pass. --approve trusts
        # project-local resources for this run; --no-session keeps runs from
        # accumulating session files in the container.
        "pi", "-p", "--mode", "json", "--approve", "--no-session",
        "--provider", provider, "--model", model, prompt,
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
    try:
        shutil.rmtree(run_dir / "workspace")
    except OSError as e:
        print(f"WARNING: could not remove {run_dir / 'workspace'}: {e}")

    eval_file = run_dir / "eval_result.json"
    grade_result = run(
        [sys.executable, str(SCRIPT_DIR / "grade.py"), str(task_dir / "task.json"),
         str(outputs_dir / "output.json"), str(duration_s), "1" if use_skills else "0"],
        capture_output=True, text=True, check=True,
    )
    eval_data = json.loads(grade_result.stdout)
    eval_data["start_time"] = start_dt.isoformat()
    eval_data["timed_out"] = timed_out
    eval_data["interrupted"] = interrupted
    eval_data["model"] = model
    eval_data["harness"] = "pi"
    eval_data["model_server"] = model_server
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
    if LOADED_FROM_ENV_FILE:
        log(f"Loaded from {env_file.ENV_FILE}: {', '.join(LOADED_FROM_ENV_FILE)}")
    # --prepare-only never starts an agent, so it needs no credential and no
    # model: it exists so run_all.py --parallel can do the shared, racy setup
    # (data fetch, image build) once and serially, before fanning out.
    if not args.prepare_only:
        key_var = HOSTED_PROVIDER_KEYS.get(args.provider)
        if key_var and not os.environ.get(key_var):
            die(f"{key_var} is not set - required for --provider {args.provider}. "
                f"Export it, or put it in {env_file.ENV_FILE}.")
        model = resolve_model(args.model, args.provider)
        model_server = get_model_server(args.provider)
    memory_gb = os.environ.get("MEMORY_GB", "8")

    task_dir = SCRIPT_DIR / args.task_name
    if args.skills and not (REPO_ROOT / "skills").exists():
        die(f"--skills was passed but {REPO_ROOT / 'skills'} doesn't exist")
    if not task_dir.is_dir():
        die(f"No such task directory: {task_dir}")
    task_json = task_dir / "task.json"
    if not task_json.is_file():
        die(f"Missing task.json in {task_dir}")
    try:
        task_config = json.loads(task_json.read_text())
    except json.JSONDecodeError:
        die(f"task.json in {task_dir} is not valid JSON")
    ensure_task_data(task_dir, task_config)

    check_docker()
    ensure_base_image()
    ensure_task_dockerfile(task_dir)

    task_image = f"pytcr-test-{args.task_name}"
    log(f"Building task image: {task_image}")
    run(["docker", "build", "-f", str(task_dir / "Dockerfile"), "-t", task_image, str(SCRIPT_DIR)], check=True)

    if args.prepare_only:
        log(f"Prepared {args.task_name} (data + image {task_image}); not running the agent.")
        sys.exit(0)

    prompt = render_prompt(task_json)

    statuses = []
    for i in range(1, args.n + 1):
        if args.n > 1:
            log(f"=== Run {i}/{args.n} ===")
        status, interrupted = run_once(
            args.task_name, task_dir, task_image, prompt, model, model_server, args.provider, memory_gb,
            args.skills, args.timeout, i, args.n, args.run_id,
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
