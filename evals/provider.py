import json
import sys
import os

# Add the backend directory to sys.path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.games.base import GameState, GameEngine
from app.games.bots.hf_pokerbot import pick_hf_poker_move
from app.games.bots.hf_chessbot import pick_hf_chess_move
from app.games.bots.hf_mahjongbot import pick_hf_mahjong_move

class DummyEngine(GameEngine):
    def __init__(self, legal_moves):
        self._legal_moves = legal_moves
        
    def get_legal_moves(self, state: GameState) -> list[str]:
        return self._legal_moves
        
    def apply_move(self, state: GameState, move: str) -> GameState:
        return state
        
    def get_winner(self, state: GameState) -> str | None:
        return None
        
    def to_dict(self, state: GameState) -> dict:
        return state.to_dict()

def call_api(prompt, options, context):
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
            move = pick_hf_chess_move(engine, state)
        elif bot_type == "mahjong":
            move = pick_hf_mahjong_move(engine, state)
        else:
            return {"error": f"Unknown bot type: {bot_type}"}
            
        return {"output": str(move)}
    except Exception as e:
        return {"error": str(e)}

