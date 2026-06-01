# Immunopeptidomics Research Agent — Implementation Plan

## Stack

| Layer | Choice | Reason |
|---|---|---|
| Agent framework | `smolagents` (HuggingFace, MIT) | Tools = plain Python functions, minimal boilerplate |
| LLM | Claude API (`claude-sonnet-4-6`) | Best tool-calling accuracy for ambiguous research queries |
| Frontend | Gradio | Browser chat UI, easy file upload, ~30 lines |

---

## File Structure

```
immunopep_agent/
├── tools/
│   ├── factory.py          # create_session() + make_tools() — closure pattern
│   ├── data_loading.py     # @tool: load MS data (TSV/CSV)
│   ├── processing.py       # @tool: filter, normalize, deduplicate
│   └── visualization.py    # @tool: length dist, volcano, sequence logos
├── agent.py                # wires tools + LiteLLM Claude backend
├── app.py                  # Gradio chat UI
└── requirements.txt
```

---

## Session Isolation Design

### Core Problem
Tool functions need access to "current dataset." A global variable causes cross-user data leakage.

### Solution: Tool Factory + `gr.State`

Each browser session gets:
- Its own `session` dict (holds the current DataFrame, session ID, workdir path)
- Its own tool closures created over that dict
- Its own `ToolCallingAgent` instance
- Its own upload directory: `uploads/<uuid>/`

All of this is stored in Gradio's `gr.State`, which is scoped to a single browser tab.

### Key Code Patterns

**Tool factory (`tools/factory.py`):**
```python
def create_session(upload_root: Path) -> dict:
    session_id = uuid.uuid4().hex
    return {
        "id": session_id,
        "df": None,
        "workdir": upload_root / session_id,
    }

def make_tools(session: dict):
    session["workdir"].mkdir(parents=True, exist_ok=True)

    @tool
    def load_data(filename: str) -> str:
        """Load immunopeptidomics MS data from an uploaded file."""
        path = session["workdir"] / filename
        session["df"] = pd.read_csv(path, sep="\t")
        return f"Loaded {len(session['df'])} rows."

    # ... more tools close over the same session dict

    return [load_data, ...]
```

**Agent initialization (`agent.py`):**
```python
def init_agent():
    session = create_session(UPLOAD_ROOT)
    tools = make_tools(session)
    agent = ToolCallingAgent(tools=tools, model=model)
    return {"agent": agent, "session": session}
```

**Gradio wiring (`app.py`):**
```python
with gr.Blocks() as demo:
    state = gr.State(new_session)   # fresh agent per tab

    chatbot = gr.Chatbot()
    msg = gr.Textbox(...)
    upload = gr.File(...)

    upload.upload(handle_upload, [upload, state], [upload_status, state])
    msg.submit(chat, [msg, chatbot, state], [msg, chatbot, state])
```

### Isolation Summary

| Concern | Mechanism |
|---|---|
| DataFrame state | `session["df"]` in closure, never global |
| Uploaded files | `uploads/<session_uuid>/` per session |
| Chat history | `gr.Chatbot` component (already per-tab) |
| Agent memory | Fresh `ToolCallingAgent` per `gr.State` init |

---

## Tools to Implement

### Data Loading
- `load_data(filename)` — read TSV/CSV from session workdir
- `list_columns()` — inspect available columns

### Processing
- `filter_by_length(min, max)` — filter peptides by sequence length
- `filter_by_score(column, threshold)` — score-based filtering
- `deduplicate()` — remove duplicate sequences
- `normalize(method)` — intensity normalization

### Visualization
- `plot_length_distribution()` — peptide length histogram
- `plot_volcano(fc_col, pval_col)` — volcano plot
- `plot_sequence_logo()` — position-weight matrix logo
- `plot_binding_scores()` — predicted affinity distribution

### Optional
- `run_netmhcpan(allele)` — binding prediction wrapper
- `export_results(format)` — save processed data

---

## Cleanup

```python
# Simple: cleanup on process exit
atexit.register(lambda: [shutil.rmtree(d, ignore_errors=True) for d in _session_dirs])

# Production: background sweep for dirs older than N hours
```

---

## Requirements

```
smolagents
litellm
anthropic
gradio
pandas
matplotlib
seaborn
logomaker       # sequence logos
```
