"""
HuggingFace-based Poker bot.
Downloads a small text-generation model and uses it to pick poker actions.
Falls back to weighted random if the model generates an invalid move.
"""

import logging
import os
import random
import threading
from typing import Optional

from app.games.base import GameEngine, GameState

# Suppress noisy HF logging
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
logging.getLogger("transformers").setLevel(logging.ERROR)

_PIPELINE = None
_LOCK = threading.Lock()
_MODEL_NAME = "sshleifer/tiny-gpt2"


def _get_pipeline():
    """Lazy-load the text-generation pipeline (thread-safe)."""
    global _PIPELINE
    with _LOCK:
        if _PIPELINE is None:
            from transformers import pipeline
            print(f"[PokerBot] Loading HuggingFace model '{_MODEL_NAME}' ...")
            _PIPELINE = pipeline(
                "text-generation",
                model=_MODEL_NAME,
                device=-1,  # CPU only
            )
            print("[PokerBot] Model loaded successfully.")
    return _PIPELINE


def _parse_raise_range(legal_moves: list[str]) -> Optional[tuple[int, int]]:
    """Extract (min, max) from a 'RAISE min max' entry if present."""
    for m in legal_moves:
        if m.startswith("RAISE "):
            parts = m.split()
            if len(parts) >= 3:
                return int(parts[1]), int(parts[2])
    return None


def _pick_raise_amount(min_r: int, max_r: int) -> int:
    """Pick a raise between min and 2x min (capped at max) for semi-sensible play."""
    return random.randint(min_r, min(min_r * 2, max_r))


def pick_hf_poker_move(engine: GameEngine, state: GameState) -> str:
    """
    Use a HuggingFace text-generation model to decide a poker action.
    The model gets a text prompt describing the game state and legal actions.
    If it generates a valid action, we use it; otherwise we fall back to
    a weighted-random strategy.
    """
    legal_moves = engine.get_legal_moves(state)
    if not legal_moves:
        raise RuntimeError("No legal moves available")

    # Build simple action names for matching
    simple_actions = []
    for m in legal_moves:
        simple_actions.append(m.split()[0])  # FOLD, CHECK, CALL, ALLIN, RAISE

    try:
        pipe = _get_pipeline()

        d = state.to_dict()
        board = d.get("board", [])
        pot = d.get("pot", 0)

        prompt = (
            f"Texas Hold'em poker. Pot: ${pot}. "
            f"Board: {', '.join(board) if board else 'none yet'}. "
            f"Available actions: {', '.join(simple_actions)}. "
            f"The optimal play is:"
        )

        output = pipe(
            prompt,
            max_new_tokens=8,
            max_length=None,
            num_return_sequences=1,
            do_sample=True,
            temperature=0.7,
            pad_token_id=pipe.tokenizer.eos_token_id,
        )
        generated = output[0]["generated_text"][len(prompt):].strip().upper()

        # Try to match the generated text to a valid action
        for action_name in ["FOLD", "CHECK", "CALL", "ALLIN", "RAISE"]:
            if action_name in generated or (action_name == "ALLIN" and "ALL" in generated and "IN" in generated):
                if action_name in simple_actions:
                    if action_name == "RAISE":
                        rng = _parse_raise_range(legal_moves)
                        if rng:
                            return f"RAISE {_pick_raise_amount(*rng)}"
                    else:
                        return action_name

    except Exception as exc:
        logging.warning(f"[PokerBot] HF inference failed: {exc}")

    # ── Weighted fallback strategy ──
    # Prefer CALL/CHECK over FOLD, occasionally RAISE
    weights = {
        "CHECK": 5,
        "CALL": 4,
        "RAISE": 2,
        "FOLD": 1,
        "ALLIN": 1,
    }
    available = [a for a in simple_actions if a in weights]
    if not available:
        # Absolute fallback
        move = random.choice(legal_moves)
        if move.startswith("RAISE "):
            rng = _parse_raise_range(legal_moves)
            if rng:
                return f"RAISE {_pick_raise_amount(*rng)}"
        return move

    w = [weights[a] for a in available]
    chosen = random.choices(available, weights=w, k=1)[0]

    if chosen == "RAISE":
        rng = _parse_raise_range(legal_moves)
        if rng:
            return f"RAISE {_pick_raise_amount(*rng)}"
        # No raise available, fall back to CALL/CHECK
        return "CALL" if "CALL" in available else "CHECK"

    return chosen
