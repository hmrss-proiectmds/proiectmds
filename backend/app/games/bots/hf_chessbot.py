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

    from transformers import AutoConfig, AutoModel
    import torch
    
    logger.info("Loading ChessBot model manually from %s ...", MODEL_DIR)
    
    _device = "cpu"
    
    try:
        config = AutoConfig.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
        _model = AutoModel.from_config(config, trust_remote_code=True)
        
        # Monkeypatch the missing attribute that causes the crash in some transformers versions
        if not hasattr(_model, 'all_tied_weights_keys'):
            _model.all_tied_weights_keys = {}

        # Find the weight file
        weight_file = MODEL_DIR / "model.safetensors"
        if weight_file.exists():
            from safetensors.torch import load_file
            state_dict = load_file(str(weight_file))
        else:
            weight_file = MODEL_DIR / "pytorch_model.bin"
            state_dict = torch.load(str(weight_file), map_location="cpu")
            
        _model.load_state_dict(state_dict, strict=False)
        _model.to(_device)
        _model.eval()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e

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
