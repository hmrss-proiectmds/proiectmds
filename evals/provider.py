"""
Promptfoo custom Python provider for game bot evaluation.

This provider invokes the platform's game bots (poker, chess, mahjong) with a
structured JSON prompt and returns the chosen move as the output string.

The bots now use the Anthropic Claude API (claude-haiku-4-5-20251001) for
move generation with shanten-minimising / weighted-random fallbacks.
"""
import json
import os
import sys

# Add the backend directory to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.games.base import GameState, GameEngine
from app.games.bots.hf_pokerbot import pick_hf_poker_move
from app.games.bots.hf_mahjongbot import pick_hf_mahjong_move


class DummyEngine(GameEngine):
    """Minimal engine stub that returns a fixed legal-moves list."""
    def __init__(self, legal_moves: list[str]):
        self._legal_moves = legal_moves

    def get_legal_moves(self, state: GameState) -> list[str]:
        return self._legal_moves

    def apply_move(self, state: GameState, move: str) -> GameState:
        return state

    def get_winner(self, state: GameState) -> str | None:
        return None

    def to_dict(self, state: GameState) -> dict:
        return state.to_dict()


def call_api(prompt: str, options: dict, context: dict) -> dict:
    """Entry point called by promptfoo for each test case."""
    try:
        data = json.loads(prompt)
        bot_type = data.get("bot")
        state_dict = data.get("state", {})
        legal_moves = data.get("legal_moves", [])

        state = GameState(game_type=bot_type, players=["bot", "p1"])
        for k, v in state_dict.items():
            state.metadata[k] = v

        engine = DummyEngine(legal_moves=legal_moves)

        if bot_type == "poker":
            move = pick_hf_poker_move(engine, state)
        elif bot_type == "chess":
            # Chess bot uses a different HF architecture; fall back to random for evals
            import random
            move = random.choice(legal_moves) if legal_moves else "e2e4"
        elif bot_type == "mahjong":
            move = pick_hf_mahjong_move(engine, state)
        else:
            return {"error": f"Unknown bot type: {bot_type}"}

        return {"output": str(move)}

    except Exception as exc:
        return {"error": str(exc)}
