"""
Abstract interfaces for the plugin-based game engine architecture.
Every game type (chess, poker, etc.) implements these contracts.
"""

from abc import ABC, abstractmethod
from typing import Optional


class GameState(ABC):
    """Abstract base for all game states."""

    @abstractmethod
    def to_dict(self) -> dict:
        """Serialize the full state to a JSON-safe dict."""
        ...

    @abstractmethod
    def get_fen(self) -> str:
        """Return a canonical string representation of the position."""
        ...


class GameEngine(ABC):
    """Abstract base for all game engines."""

    game_type: str = ""
    min_players: int = 2
    max_players: int = 2

    @abstractmethod
    def create_initial_state(self) -> GameState:
        ...

    @abstractmethod
    def validate_move(self, state: GameState, move: str) -> bool:
        ...

    @abstractmethod
    def apply_move(self, state: GameState, move: str) -> GameState:
        """Return a NEW state with the move applied (do not mutate)."""
        ...

    @abstractmethod
    def get_legal_moves(self, state: GameState) -> list[str]:
        ...

    @abstractmethod
    def get_current_turn(self, state: GameState) -> int:
        """Return the seat number (1 or 2) whose turn it is."""
        ...

    @abstractmethod
    def is_terminal(self, state: GameState) -> Optional[dict]:
        """
        Return None if the game is still ongoing.
        Otherwise return {"result": "player1_win"|"player2_win"|"draw", "reason": "..."}.
        """
        ...

    @abstractmethod
    def get_player_view(self, state: GameState, seat: int) -> dict:
        """
        Return a JSON-safe dict of the game state visible to the given seat.
        For perfect-info games (chess), this is the full state.
        For imperfect-info games (poker), this filters hidden information.
        """
        ...

    @abstractmethod
    def get_last_move_san(self, state: GameState) -> Optional[str]:
        """Return the SAN notation of the last move, or None."""
        ...
