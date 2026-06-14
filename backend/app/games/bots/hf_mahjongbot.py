"""
Claude-based Riichi Mahjong bot (replaces the former HuggingFace tiny-gpt2 bot).

Primary strategy: shanten-minimising heuristic (unchanged from the HF version).
Claude is asked to choose the optimal discard tile; if the response is valid it
is used, otherwise the shanten heuristic fallback is applied.

Riichi / Tsumo rules are handled deterministically as before.
"""

from __future__ import annotations

import logging
import random
from typing import Optional

from app.games.base import GameEngine, GameState
from app.games.mahjong.engine import (
    shanten,
    riichi_candidates,
    tile_display,
    ALL_34,
)

logger = logging.getLogger(__name__)

_CLAUDE_MODEL = "claude-haiku-4-5-20251001"


def _get_api_key() -> str:
    from app.config import settings
    return settings.ANTHROPIC_API_KEY


# ── Heuristic helpers ──────────────────────────────────────────────────────────

def _best_shanten_discard(hand_14: list[str], legal_discards: list[str]) -> str:
    """Return the discard tile that minimises shanten number."""
    best_sh = 9
    best_tile: Optional[str] = None
    for move in legal_discards:
        tile = move[8:]  # strip "DISCARD_"
        remaining = list(hand_14)
        remaining.remove(tile)
        sh = shanten(remaining)
        if sh < best_sh or best_tile is None:
            best_sh = sh
            best_tile = tile
    return best_tile or legal_discards[0][8:]


def _claude_discard(hand_14: list[str]) -> Optional[str]:
    """Ask Claude to suggest the best discard tile."""
    api_key = _get_api_key()
    if not api_key:
        return None

    hand_str = " ".join(hand_14)
    prompt = (
        f"You are playing Riichi Mahjong.\n"
        f"Your 14-tile hand: {hand_str}\n"
        f"Which single tile should you discard to get closest to tenpai?\n"
        f"Reply with ONLY the tile notation (e.g. '3m', '5p', '7s', '1z')."
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_CLAUDE_MODEL,
            max_tokens=8,
            messages=[{"role": "user", "content": prompt}],
        )
        generated = response.content[0].text.strip()
        for tile in ALL_34:
            if tile in generated and tile in hand_14:
                return tile
    except Exception as exc:
        logger.warning("[MahjongBot] Claude API failed: %s", exc)
    return None


# ── Public entry point ─────────────────────────────────────────────────────────

def pick_hf_mahjong_move(engine: GameEngine, state: GameState) -> str:
    """
    Choose the best move for the current mahjong player.
    Called by game_manager.make_ai_move when bot_type == 'mahjongbot'.
    """
    legal = engine.get_legal_moves(state)
    if not legal:
        raise RuntimeError("No legal moves available")

    if "TSUMO" in legal:
        return "TSUMO"

    seat = state.current_seat
    hand14 = list(state.hands.get(seat, []))

    riichi_moves = [m for m in legal if m.startswith("RIICHI_")]
    if riichi_moves:
        return riichi_moves[0]

    discard_moves = [m for m in legal if m.startswith("DISCARD_")]
    if not discard_moves:
        return legal[0]

    claude_tile = _claude_discard(hand14)
    if claude_tile:
        candidate = f"DISCARD_{claude_tile}"
        if candidate in discard_moves:
            return candidate

    best = _best_shanten_discard(hand14, discard_moves)
    return f"DISCARD_{best}"
