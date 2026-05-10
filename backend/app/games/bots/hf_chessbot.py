"""
HuggingFace ChessBot integration.
Loads the Maxlegrec/ChessBot model (locally cached) and uses it
to predict chess moves from FEN positions.

Model: https://huggingface.co/Maxlegrec/ChessBot
- Transformer trained on 750M positions from LCZero project
- Takes FEN → outputs UCI move with legal-move filtering
- Temperature T controls play strength (lower = stronger)
"""

from __future__ import annotations

import logging
from pathlib import Path

import chess
import torch

from app.games.base import GameEngine, GameState

logger = logging.getLogger(__name__)

# ── Lazy-loaded singleton ──
_model = None
_device = None

MODEL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models" / "chessbot"


def _load_model():
    """Lazy-load the ChessBot model on first use."""
    global _model, _device

    if _model is not None:
        return _model, _device

    if not MODEL_DIR.exists():
        raise FileNotFoundError(
            f"ChessBot model not found at {MODEL_DIR}. "
            "Run: python -c \"from huggingface_hub import snapshot_download; "
            "snapshot_download('Maxlegrec/ChessBot', local_dir='models/chessbot')\""
        )

    from transformers import AutoModel

    logger.info("Loading ChessBot model from %s ...", MODEL_DIR)
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = AutoModel.from_pretrained(
        str(MODEL_DIR), trust_remote_code=True
    ).to(_device)
    _model.eval()
    logger.info("ChessBot loaded on %s", _device)
    return _model, _device


def pick_hf_move(engine: GameEngine, state: GameState, temperature: float = 0.3) -> str:
    """
    Use the HuggingFace ChessBot to pick a move.
    Falls back to random if the model produces an illegal move.
    """
    model, device = _load_model()
    fen = state.get_fen()

    with torch.no_grad():
        move_uci = model.get_move_from_fen_no_thinking(
            fen, T=temperature, device=device, force_legal=True
        )

    # Validate the move is legal (model already filters, but double-check)
    board = chess.Board(fen)
    try:
        m = chess.Move.from_uci(move_uci)
        if m not in board.legal_moves:
            # Knight promotion fix: model strips 'n' suffix
            for legal in board.legal_moves:
                if legal.uci().startswith(move_uci):
                    return legal.uci()
            # Fall back to random
            logger.warning("ChessBot produced illegal move %s, falling back to random", move_uci)
            from app.games.bots.random_bot import pick_random_move
            return pick_random_move(engine, state)
    except (ValueError, chess.InvalidMoveError):
        logger.warning("ChessBot produced unparseable move %s, falling back to random", move_uci)
        from app.games.bots.random_bot import pick_random_move
        return pick_random_move(engine, state)

    return move_uci


def is_available() -> bool:
    """Check if the ChessBot model files exist locally."""
    return MODEL_DIR.exists() and (MODEL_DIR / "model.safetensors").exists()
