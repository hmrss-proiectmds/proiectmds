"""
HuggingFace-based Chess bot.
Downloads a small text-generation model and uses it to pick chess moves.
Falls back to random if the model generates an invalid move.
"""

from __future__ import annotations

import logging
import os
import random
import threading
from typing import Optional

import chess
from app.games.base import GameEngine, GameState

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
            print(f"[ChessBot] Loading HuggingFace model '{_MODEL_NAME}' ...")
            _PIPELINE = pipeline(
                "text-generation",
                model=_MODEL_NAME,
                device=-1,  # CPU only
            )
            print("[ChessBot] Model loaded successfully.")
    return _PIPELINE

def pick_hf_move(engine: GameEngine, state: GameState, temperature: float = 0.3) -> str:
    """
    Use a HuggingFace text-generation model to decide a chess move.
    """
    legal_moves = engine.get_legal_moves(state)
    if not legal_moves:
        raise RuntimeError("No legal moves available")

    try:
        pipe = _get_pipeline()
        fen = state.get_fen()

        prompt = (
            f"Chess game. Current FEN: {fen}. "
            f"Legal moves: {', '.join(legal_moves)}. "
            f"The best move is:"
        )

        output = pipe(
            prompt,
            max_new_tokens=6,
            max_length=None,
            num_return_sequences=1,
            do_sample=True,
            temperature=temperature,
            pad_token_id=pipe.tokenizer.eos_token_id,
        )
        generated = output[0]["generated_text"][len(prompt):].strip()
        
        # Parse the output
        parts = generated.split()
        if parts:
            gen_move = parts[0]
            for move in legal_moves:
                if gen_move.startswith(move) or move.startswith(gen_move):
                    return move
                    
    except Exception as exc:
        logging.warning(f"[ChessBot] HF inference failed: {exc}")

    # Fallback to random
    logging.warning("[ChessBot] Produced unparseable move, falling back to random")
    from app.games.bots.random_bot import pick_random_move
    return pick_random_move(engine, state)

def is_available() -> bool:
    """Check if the ChessBot model is available."""
    return True
