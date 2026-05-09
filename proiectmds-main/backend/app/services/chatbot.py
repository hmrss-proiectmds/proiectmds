"""
Chatbot service — loads a HuggingFace text-generation model and uses a
markdown file as the system prompt for personality and platform knowledge.
"""

import logging
import os
import threading
from pathlib import Path

# Suppress noisy HF logging
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
logging.getLogger("transformers").setLevel(logging.ERROR)

_MODEL_NAME = "HuggingFaceTB/SmolLM2-360M-Instruct"
_PIPELINE = None
_LOCK = threading.Lock()
_SYSTEM_PROMPT: str | None = None

# Path to the system prompt markdown file
_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "chatbot_prompt.md"


def _load_system_prompt() -> str:
    """Read the markdown system prompt file."""
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        try:
            _SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
            print(f"[ChatBot] Loaded system prompt from {_PROMPT_PATH} ({len(_SYSTEM_PROMPT)} chars)")
        except FileNotFoundError:
            _SYSTEM_PROMPT = "You are a helpful assistant for a game platform."
            print(f"[ChatBot] Warning: {_PROMPT_PATH} not found, using fallback prompt")
    return _SYSTEM_PROMPT


def _get_pipeline():
    """Lazy-load the text-generation pipeline (thread-safe)."""
    global _PIPELINE
    with _LOCK:
        if _PIPELINE is None:
            from transformers import pipeline
            print(f"[ChatBot] Loading HuggingFace model '{_MODEL_NAME}' ...")
            _PIPELINE = pipeline(
                "text-generation",
                model=_MODEL_NAME,
                device=-1,  # CPU
            )
            print("[ChatBot] Model loaded successfully.")
    return _PIPELINE


def generate_reply(user_messages: list[dict]) -> str:
    """
    Generate a chatbot reply.

    Args:
        user_messages: List of {"role": "user"|"assistant", "content": "..."} dicts.
                       The system prompt is prepended automatically.

    Returns:
        The assistant's reply string.
    """
    system_prompt = _load_system_prompt()
    pipe = _get_pipeline()

    # Build the full message list: system + conversation history
    messages = [{"role": "system", "content": system_prompt}]
    for msg in user_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content.strip():
            messages.append({"role": role, "content": content})

    try:
        output = pipe(
            messages,
            max_new_tokens=200,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )
        # The pipeline returns the full conversation; extract the last assistant message
        generated = output[0]["generated_text"]
        if isinstance(generated, list):
            # Chat-style output: list of message dicts
            assistant_msgs = [m for m in generated if m.get("role") == "assistant"]
            if assistant_msgs:
                return assistant_msgs[-1]["content"].strip()
        elif isinstance(generated, str):
            # Raw text output — extract everything after the last user message
            return generated.strip()

        return "I'm not sure how to answer that. Could you rephrase?"

    except Exception as exc:
        logging.error(f"[ChatBot] Generation failed: {exc}")
        return "Sorry, I ran into an issue generating a response. Please try again!"
