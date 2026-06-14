"""
Chatbot service — uses the Anthropic Claude API (claude-haiku-4-5) with a
markdown file as the system prompt for personality and platform knowledge.

Falls back to a static error message when ANTHROPIC_API_KEY is not configured.
"""

import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT: str | None = None
_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "chatbot_prompt.md"
_CLAUDE_MODEL = "claude-haiku-4-5-20251001"


def _load_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        try:
            _SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            _SYSTEM_PROMPT = "You are a helpful assistant for a game platform."
    return _SYSTEM_PROMPT


def generate_reply(user_messages: list[dict]) -> str:
    """
    Generate a chatbot reply via the Anthropic Claude API.

    Args:
        user_messages: List of {"role": "user"|"assistant", "content": "..."} dicts.

    Returns:
        The assistant's reply string.
    """
    if not settings.ANTHROPIC_API_KEY:
        return (
            "The AI assistant is not configured. "
            "Please set the ANTHROPIC_API_KEY environment variable."
        )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        system_prompt = _load_system_prompt()

        messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in user_messages
            if msg.get("role") in ("user", "assistant") and msg.get("content", "").strip()
        ]

        if not messages:
            return "Please send a message to start the conversation."

        response = client.messages.create(
            model=_CLAUDE_MODEL,
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text.strip()

    except Exception as exc:
        logger.error(f"[ChatBot] Claude API call failed: {exc}")
        return "Sorry, I ran into an issue generating a response. Please try again!"
