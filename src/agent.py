import os
from pathlib import Path

from dotenv import load_dotenv
import importlib.resources
import yaml
from smolagents import ToolCallingAgent, LiteLLMModel
from smolagents.models import ChatMessage

load_dotenv(Path(__file__).parent.parent / "local.env")

from tools.factory import create_session, make_tools

UPLOAD_ROOT = Path(__file__).parent / "uploads"

class _OllamaNoThinkModel(LiteLLMModel):
    """LiteLLMModel wrapper that disables Qwen3 extended thinking."""

    def generate(self, messages, **kwargs) -> ChatMessage:
        kwargs.setdefault("extra_body", {})["think"] = False
        return super().generate(messages, **kwargs)


_anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
if _anthropic_key:
    _model = LiteLLMModel(model_id="claude-sonnet-4-6", api_key=_anthropic_key)
else:
    _ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3.6:latest")
    _model = _OllamaNoThinkModel(model_id=f"ollama/{_ollama_model}", timeout=120)

SYSTEM_PROMPT = """You are an immunopeptidomics research assistant.
You help scientists load, inspect, and analyse T-cell receptor (TCR) repertoire data.
Data is stored in pyTCR standardised format with columns:
  sample, freq, #count, cdr3aa, cdr3nt, v, d, j

When the user uploads a file it is automatically loaded and you receive a summary.
Use the available tools to answer questions about the data.
Be concise and scientific in your responses."""


def init_agent() -> dict:
    """Create a fresh, session-isolated agent. Call once per browser tab."""
    session = create_session(UPLOAD_ROOT)
    tools = make_tools(session)
    templates = yaml.safe_load(
        importlib.resources.files("smolagents.prompts")
        .joinpath("toolcalling_agent.yaml")
        .read_text()
    )
    templates["system_prompt"] += "\n\n" + SYSTEM_PROMPT

    agent = ToolCallingAgent(
        tools=tools,
        model=_model,
        prompt_templates=templates,
        max_steps=6,
        verbosity_level=0,
    )
    return {"agent": agent, "session": session}
