"""
Random-move bot — picks a uniformly random legal move.
Used as the simplest built-in AI opponent for testing.
"""

import random

from app.games.base import GameEngine, GameState


def pick_random_move(engine: GameEngine, state: GameState) -> str:
    """Return a random legal move in UCI notation."""
    moves = engine.get_legal_moves(state)
    if not moves:
        raise RuntimeError("No legal moves available")
    return random.choice(moves)
