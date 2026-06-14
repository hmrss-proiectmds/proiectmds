"""
Claude-based Poker bot (replaces the former HuggingFace tiny-gpt2 bot).

Primary strategy: ask claude-haiku-4-5 to pick the best action given the
current board and pot, choosing from the legal moves list.
Falls back to weighted-random when the API is unavailable or the key is
not configured.
"""

from __future__ import annotations

import logging
import os
import random
from typing import Optional

from app.games.base import GameEngine, GameState

logger = logging.getLogger(__name__)

_CLAUDE_MODEL = "claude-haiku-4-5-20251001"


def _get_api_key() -> str:
    from app.config import settings
    return settings.ANTHROPIC_API_KEY


def _parse_raise_range(legal_moves: list[str]) -> Optional[tuple[int, int]]:
    """Extract (min, max) from a 'RAISE min max' entry if present."""
    for m in legal_moves:
        if m.startswith("RAISE "):
            parts = m.split()
            if len(parts) >= 3:
                return int(parts[1]), int(parts[2])
    return None


def _pick_raise_amount(min_r: int, max_r: int) -> int:
    return random.randint(min_r, min(min_r * 2, max_r))


def _weighted_fallback(legal_moves: list[str]) -> str:
    simple_actions = [m.split()[0] for m in legal_moves]
    weights = {"CHECK": 5, "CALL": 4, "RAISE": 2, "FOLD": 1, "ALLIN": 1}
    available = [a for a in simple_actions if a in weights]
    if not available:
        move = random.choice(legal_moves)
        if move.startswith("RAISE "):
            rng = _parse_raise_range(legal_moves)
            if rng:
                return f"RAISE {_pick_raise_amount(*rng)}"
        return move
    chosen = random.choices(available, weights=[weights[a] for a in available], k=1)[0]
    if chosen == "RAISE":
        rng = _parse_raise_range(legal_moves)
        if rng:
            return f"RAISE {_pick_raise_amount(*rng)}"
        return "CALL" if "CALL" in available else "CHECK"
    return chosen


def pick_hf_poker_move(engine: GameEngine, state: GameState) -> str:
    """
    Use Claude to decide the best poker action.
    Falls back to weighted-random when Claude is unavailable.
    """
    legal_moves = engine.get_legal_moves(state)
    if not legal_moves:
        raise RuntimeError("No legal moves available")

    api_key = _get_api_key()
    if not api_key:
        logger.warning("[PokerBot] ANTHROPIC_API_KEY not set — using weighted fallback")
        return _weighted_fallback(legal_moves)

    simple_actions = [m.split()[0] for m in legal_moves]
    d = state.to_dict()
    board = d.get("board", [])
    pot = d.get("pot", 0)

    prompt = (
        f"You are playing Texas Hold'em poker.\n"
        f"Community cards on board: {', '.join(board) if board else 'none yet'}.\n"
        f"Current pot: ${pot}.\n"
        f"Available actions: {', '.join(simple_actions)}.\n"
        f"Reply with ONLY the action name (e.g. CALL, FOLD, RAISE, CHECK, ALLIN)."
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_CLAUDE_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        generated = response.content[0].text.strip().upper()

        for action_name in ["FOLD", "CHECK", "CALL", "ALLIN", "RAISE"]:
            if action_name in generated and action_name in simple_actions:
                if action_name == "RAISE":
                    rng = _parse_raise_range(legal_moves)
                    if rng:
                        return f"RAISE {_pick_raise_amount(*rng)}"
                else:
                    return action_name

    except Exception as exc:
        logger.warning(f"[PokerBot] Claude API failed: {exc}")

    return _weighted_fallback(legal_moves)
