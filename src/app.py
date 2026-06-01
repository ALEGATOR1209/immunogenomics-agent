import shutil
import sys
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).parent))

from agent import init_agent
from tools.data_loading import load_pytcr_file


def handle_upload(file, state: dict) -> tuple[str, list, dict]:
    """Save uploaded file, auto-load it, and post the summary into chat."""
    if file is None:
        return state["summary"], state["history"], state

    src = Path(file.name)
    dest = state["session"]["workdir"] / src.name
    shutil.copy(src, dest)

    try:
        df, summary = load_pytcr_file(dest)
        state["session"]["df"] = df
        state["session"]["filename"] = src.name
    except Exception as exc:
        summary = f"**Error loading file:** {exc}"

    state["summary"] = summary
    state["history"] = state["history"] + [
        {"role": "assistant", "content": f"File uploaded.\n\n{summary}"}
    ]
    return summary, state["history"], state


def handle_message(message: str, state: dict) -> tuple[str, list, dict]:
    if not message.strip():
        return "", state["history"], state

    try:
        response = state["agent"].run(message)
    except Exception as exc:
        response = f"Agent error: {exc}"

    state["history"] = state["history"] + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": str(response)},
    ]
    return "", state["history"], state


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
                label="Upload repertoire file (.tsv / .csv)",
                file_types=[".tsv", ".csv"],
            )
            summary_box = gr.Markdown(label="Dataset summary", value="_No file loaded yet._")

        with gr.Column(scale=2):
            chatbot = gr.Chatbot(height=480)
            msg_box = gr.Textbox(
                placeholder="Ask about your data…",
                label="Message",
                lines=1,
            )
            send_btn = gr.Button("Send", variant="primary")

    upload.upload(
        handle_upload,
        inputs=[upload, state],
        outputs=[summary_box, chatbot, state],
    )
    send_btn.click(
        handle_message,
        inputs=[msg_box, state],
        outputs=[msg_box, chatbot, state],
    )
    msg_box.submit(
        handle_message,
        inputs=[msg_box, state],
        outputs=[msg_box, chatbot, state],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
