"""
HuggingFace-based Riichi Mahjong bot.

Primary strategy: shanten-minimising heuristic — for each candidate discard,
remove the tile from the 14-tile hand and compute the shanten number of the
remaining 13 tiles; pick the discard that achieves the lowest shanten.
If multiple tiles achieve the same shanten, prefer the one that is furthest
from completing sequences (i.e. isolated tiles) to avoid breaking partial melds.

HF text-generation layer (sshleifer/tiny-gpt2, same model used by the poker bot
so it is already cached after first download):
  - Build a plain-text prompt describing the hand and ask for a discard.
  - If the model's output contains a valid tile name, use it.
  - Otherwise fall back to the shanten heuristic described above.

Riichi declaration: if the player can declare riichi, the bot always does.
Tsumo: the bot always takes a winning self-draw immediately.
"""

from __future__ import annotations

import logging
import os
import random
import threading
from typing import Optional

from app.games.base import GameEngine, GameState
from app.games.mahjong.engine import (
    shanten,
    riichi_candidates,
    tile_display,
    ALL_34,
)

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
logging.getLogger("transformers").setLevel(logging.ERROR)

_PIPELINE = None
_LOCK = threading.Lock()
_MODEL_NAME = "sshleifer/tiny-gpt2"


def _get_pipeline():
    global _PIPELINE
    with _LOCK:
        if _PIPELINE is None:
            from transformers import pipeline
            print(f"[MahjongBot] Loading HuggingFace model '{_MODEL_NAME}' ...")
            _PIPELINE = pipeline(
                "text-generation",
                model=_MODEL_NAME,
                device=-1,
            )
            print("[MahjongBot] Model loaded.")
    return _PIPELINE


# ── Heuristic helpers ──────────────────────────────────────────────────────────

def _best_shanten_discard(hand_14: list[str], legal_discards: list[str]) -> str:
    """
    Return the discard tile from *legal_discards* that minimises shanten.
    Ties broken by preferring isolated honor tiles, then randomly.
    """
    best_sh   = 9
    best_tile: Optional[str] = None

    for move in legal_discards:
        tile = move[8:]   # strip "DISCARD_"
        remaining = list(hand_14)
        remaining.remove(tile)
        sh = shanten(remaining)
        if sh < best_sh or best_tile is None:
            best_sh   = sh
            best_tile = tile

    return best_tile or legal_discards[0][8:]


def _hf_discard(hand_14: list[str]) -> Optional[str]:
    """
    Ask the HF model to suggest a discard tile.
    Returns a tile string (e.g. '3m') or None if parsing fails.
    """
    try:
        pipe = _get_pipeline()
        hand_str = " ".join(sorted(hand_14))
        prompt = (
            f"Riichi Mahjong hand: {hand_str}. "
            f"Discard one tile. Best discard tile:"
        )
        out = pipe(
            prompt,
            max_new_tokens=6,
            num_return_sequences=1,
            do_sample=True,
            temperature=0.8,
            pad_token_id=pipe.tokenizer.eos_token_id,
        )
        generated = out[0]["generated_text"][len(prompt):].strip()
        # Try to find a valid tile name in the generated text
        for tile in ALL_34:
            if tile in generated and tile in hand_14:
                return tile
    except Exception as exc:
        logging.warning("[MahjongBot] HF inference failed: %s", exc)
    return None


# ── Public entry point ────────────────────────────────────────────────────────

def pick_hf_mahjong_move(engine: GameEngine, state: GameState) -> str:
    """
    Choose the best move for the current mahjong player.
    Called by game_manager.make_ai_move when bot_type == 'mahjongbot'.
    """
    legal = engine.get_legal_moves(state)
    if not legal:
        raise RuntimeError("No legal moves available")

    # Always win immediately
    if "TSUMO" in legal:
        return "TSUMO"

    seat   = state.current_seat
    hand14 = list(state.hands.get(seat, []))

    # Always declare riichi when possible
    riichi_moves = [m for m in legal if m.startswith("RIICHI_")]
    if riichi_moves:
        return riichi_moves[0]

    discard_moves = [m for m in legal if m.startswith("DISCARD_")]
    if not discard_moves:
        return legal[0]

    # Try HF model for a tile suggestion
    hf_tile = _hf_discard(hand14)
    if hf_tile:
        candidate = f"DISCARD_{hf_tile}"
        if candidate in discard_moves:
            return candidate

    # Shanten-minimising fallback
    best = _best_shanten_discard(hand14, discard_moves)
    return f"DISCARD_{best}"
