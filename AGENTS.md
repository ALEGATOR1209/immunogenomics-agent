# AGENTS.md — TCR Repertoire Research Assistant

## Overview

A Gradio chat UI backed by a `smolagents` `ToolCallingAgent` that lets researchers load, inspect, and visualise T-cell receptor (TCR) repertoire data through plain-text requests.

---

## Running

```bash
# Install dependencies (once)
pip install -r requirements.txt

# Start (from project root)
python src/app.py
```

Open `http://127.0.0.1:7860` in a browser.

### LLM backend

The agent selects the model automatically:

| Condition | Model used |
|---|---|
| `ANTHROPIC_API_KEY` set in `local.env` | `claude-sonnet-4-6` via LiteLLM |
| No API key | `qwen3.6:latest` via local Ollama |

Override the Ollama model:
```bash
OLLAMA_MODEL=llama3.1:8b python src/app.py
```

`local.env` is read from the project root and is git-ignored.

---

## Architecture

```
src/
├── app.py              # Gradio UI — layout, event handlers, session wiring
├── agent.py            # Model selection, agent initialisation (one agent per browser tab)
└── tools/
    ├── data_loading.py # Pure functions: file parsing, column detection, combine_files
    └── factory.py      # make_tools() — creates tool closures over a session dict
```

### Session isolation

Each browser tab gets its own isolated state via `gr.State`:

- A `session` dict containing `df` (current DataFrame), `workdir` (`uploads/<uuid>/`), `last_view`, `last_plot`
- A `ToolCallingAgent` instance whose tools close over that session dict
- Uploaded files stored under `uploads/<session_uuid>/`

No global mutable state is used. Tool functions never reference module-level variables for data.

---

## Tools

All tools are defined in `src/tools/factory.py` via the closure pattern. Each tool receives no session argument directly — they close over the `session` dict created for that tab.

| Tool | Trigger phrases | Description |
|---|---|---|
| `load_data(filenames)` | "load file X", "reload sample A and B" | Load one or more uploaded files by name, combine into one DataFrame |
| `describe_data()` | "describe the data", "what columns do I have" | Shape, column list, first 3 rows |
| `remap_columns(mapping)` | "rename column X to Y" | Manually fix auto-detection failures; format: `"old:new, old2:new2"` |
| `show_data(n, sort_by, ascending)` | "show head", "sort by freq descending, show top 20" | Tabular view of N rows with optional sort; result stored in `session["last_view"]` |
| `plot_clonotypes_per_sample()` | "plot clonotypes per sample", "sample sizes" | Bar chart: samples × clonotype count; PNG saved to session workdir |
| `plot_cdr3aa_length_distribution()` | "CDR3 length distribution", "cdr3aa vs counts" | Bar chart: CDR3aa length × clonotype count |

Plots are saved to `uploads/<session_uuid>/plots/` and surfaced via `session["last_plot"]`, which the Gradio handler passes to the `gr.Image` component after every message.

---

## pyTCR column standard

Files are automatically remapped to this schema on load:

| Column | Description |
|---|---|
| `sample` | Sample name (injected from filename if absent) |
| `freq` | Clonotype frequency (share of repertoire) |
| `#count` | Raw read / template count |
| `cdr3aa` | CDR3 amino acid sequence |
| `cdr3nt` | CDR3 nucleotide sequence |
| `v` | V gene |
| `d` | D gene |
| `j` | J gene |

Column aliases for common platforms (MiXCR, Adaptive Immunosequencing, IMGT, etc.) are defined in `data_loading.COLUMN_ALIASES`. Unresolvable columns are reported to the user with a list of available columns, and can be fixed via the `remap_columns` tool.

---

## Multi-file upload

Uploading several files at once combines them into one DataFrame:

1. Each file is saved to `uploads/<session_uuid>/`
2. `combine_files()` loads each independently and concatenates with `pd.concat`
3. If a file lacks a `sample` column, the filename stem is used as the sample name
4. A combined summary (total clonotypes, unique samples, total reads) is shown alongside per-file summaries

---

## Adding a new tool

1. Define the function inside `make_tools()` in `src/tools/factory.py`, decorated with `@tool`
2. Close over `session` for any state (DataFrame, workdir, last_view/plot)
3. Write a clear docstring — the agent uses it to decide when to call the tool
4. Append the function to the `return` list at the bottom of `make_tools()`

Example:
```python
@tool
def my_tool(arg: str) -> str:
    """
    Short description used by the agent for tool selection.

    Args:
        arg: What this argument means.
    """
    df = session["df"]
    if df is None:
        return "No data loaded yet."
    # ... do work ...
    return "Result"
```
