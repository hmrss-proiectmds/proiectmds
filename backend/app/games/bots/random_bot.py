"""
Random-move bot — picks a uniformly random legal move.
Used as the simplest built-in AI opponent for testing.
Handles both chess (UCI) and poker (FOLD/CALL/CHECK/RAISE) moves.
"""

import random

from app.games.base import GameEngine, GameState


def pick_random_move(engine: GameEngine, state: GameState) -> str:
    """Return a random legal move."""
    moves = engine.get_legal_moves(state)
    if not moves:
        raise RuntimeError("No legal moves available")

    move = random.choice(moves)

    # If it's a RAISE range like "RAISE 20 490", pick a random amount
    if move.startswith("RAISE "):
        parts = move.split()
        if len(parts) >= 3:
            min_r = int(parts[1])
            max_r = int(parts[2])
            # Bias toward smaller raises for more realistic play
            raise_amt = random.randint(min_r, min(min_r * 3, max_r))
            return f"RAISE {raise_amt}"

    return move
