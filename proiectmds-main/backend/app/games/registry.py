"""
Dynamic game type registry.
Import and register all game engines here.
"""

from app.games.base import GameEngine

_ENGINES: dict[str, GameEngine] = {}


def register_engine(engine: GameEngine) -> None:
    _ENGINES[engine.game_type] = engine


def get_engine(game_type: str) -> GameEngine:
    engine = _ENGINES.get(game_type)
    if engine is None:
        raise ValueError(f"Unknown game type: {game_type}. Available: {list(_ENGINES.keys())}")
    return engine


def list_game_types() -> list[str]:
    return list(_ENGINES.keys())


# ── Auto-register engines on import ──
def _bootstrap() -> None:
    from app.games.chess.engine import ChessEngine
    register_engine(ChessEngine())

    from app.games.poker.engine import PokerEngine
    register_engine(PokerEngine())


_bootstrap()
