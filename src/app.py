import os
import shutil
import sys
from pathlib import Path

# Must be set before gradio is imported
_gradio_tmp = Path.home() / ".cache" / "gradio"
_gradio_tmp.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("GRADIO_TEMP_DIR", str(_gradio_tmp))

import gradio as gr

sys.path.insert(0, str(Path(__file__).parent))

from agent import init_agent
from tools.data_loading import combine_files


def handle_upload(files, state: dict):
    if not files:
        return state["summary"], state["history"], _current_view(state), _current_plot(state), state

    # files is a list of NamedString / tempfile objects
    saved: list[Path] = []
    for f in files:
        src = Path(f.name)
        dest = state["session"]["workdir"] / src.name
        shutil.copy(src, dest)
        saved.append(dest)

    try:
        df, summary = combine_files(saved)
        state["session"]["df"] = df
        state["session"]["filenames"] = [p.name for p in saved]
    except Exception as exc:
        summary = f"**Error loading files:** {exc}"
        df = None

    state["summary"] = summary
    state["history"] = state["history"] + [
        {"role": "assistant", "content": f"Files uploaded.\n\n{summary}"}
    ]
    if df is not None:
        state["session"]["last_view"] = df.head(10)
    return summary, state["history"], _current_view(state), _current_plot(state), state


def handle_message(message: str, state: dict):
    if not message.strip():
        return "", state["history"], _current_view(state), _current_plot(state), state

    try:
        response = state["agent"].run(message)
    except Exception as exc:
        response = f"Agent error: {exc}"

    state["history"] = state["history"] + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": str(response)},
    ]
    return "", state["history"], _current_view(state), _current_plot(state), state


def _current_view(state: dict):
    return state["session"].get("last_view")


def _current_plot(state: dict):
    return state["session"].get("last_plot")


def new_state() -> dict:
    agent_bundle = init_agent()
    return {**agent_bundle, "history": [], "summary": ""}


with gr.Blocks(title="TCR Repertoire Assistant") as demo:
    gr.Markdown("## TCR Repertoire Research Assistant")
    gr.Markdown(
        "Upload a repertoire file (TSV or CSV) — it will be loaded automatically. "
        "Then ask questions in the chat."
    )

    state = gr.State(new_state)

    with gr.Row():
        with gr.Column(scale=1):
            upload = gr.File(
                label="Upload repertoire files (.tsv / .csv)",
                file_types=[".tsv", ".csv"],
                file_count="multiple",
            )
            summary_box = gr.Markdown(label="Dataset summary", value="_No file loaded yet._")

        with gr.Column(scale=2):
            chatbot = gr.Chatbot(height=400)
            msg_box = gr.Textbox(
                placeholder="Ask about your data…",
                label="Message",
                lines=1,
            )
            send_btn = gr.Button("Send", variant="primary")

    with gr.Row():
        data_view = gr.DataFrame(label="Data view", wrap=True)
        plot_view = gr.Image(label="Plot", visible=True)

    upload.upload(
        handle_upload,
        inputs=[upload, state],
        outputs=[summary_box, chatbot, data_view, plot_view, state],
    )
    send_btn.click(
        handle_message,
        inputs=[msg_box, state],
        outputs=[msg_box, chatbot, data_view, plot_view, state],
    )
    msg_box.submit(
        handle_message,
        inputs=[msg_box, state],
        outputs=[msg_box, chatbot, data_view, plot_view, state],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
