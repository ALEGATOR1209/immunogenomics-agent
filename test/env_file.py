"""Loads the repo-root .env into os.environ, for test.py and run_all.py.

The harness is configured entirely through environment variables
(ANTHROPIC_API_KEY, MODEL, MEMORY_GB, LLAMA_BASE_URL, HOST_LLAMA_URL), which
otherwise have to be re-exported in every shell that starts a run. .env is
gitignored, so it's the natural place to keep a machine's own values -
particularly the API key, which must not end up in a shell history or a
committed file.

Deliberately a hand-rolled parser rather than python-dotenv: these scripts run
with whatever Python the host happens to have and have no dependencies to
install, and the file only ever holds plain KEY=VALUE lines.

A variable already present in the environment always wins, so an explicit
`MODEL=... ./test.py ...` still overrides the file.
"""
import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def parse_env_file(path):
    """KEY=VALUE lines -> dict. Skips blanks and # comments, tolerates a
    leading `export `, and strips one layer of matching quotes around the
    value. Malformed lines (no `=`) are ignored rather than fatal - a
    half-written .env shouldn't stop a sweep that doesn't need it."""
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def load_env(path=ENV_FILE):
    """Sets any variable from `path` that isn't already in os.environ.
    Returns the names it set (empty when there's no file), so callers can say
    what was picked up without ever printing a value."""
    if not path.is_file():
        return []
    loaded = []
    for key, value in parse_env_file(path).items():
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded
