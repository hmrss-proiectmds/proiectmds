"""
Chess game engine powered by python-chess.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional

import chess

from app.games.base import GameEngine, GameState


# ── Piece map for JSON board representation ──
_PIECE_MAP = {
    chess.PAWN: "p", chess.KNIGHT: "n", chess.BISHOP: "b",
    chess.ROOK: "r", chess.QUEEN: "q", chess.KING: "k",
}


@dataclass
class ChessState(GameState):
    """Wraps a python-chess Board as our GameState."""

    board: chess.Board = field(default_factory=chess.Board)
    _last_move_san: Optional[str] = field(default=None, repr=False)
    _move_stack_san: list[str] = field(default_factory=list, repr=False)

    def to_dict(self) -> dict:
        return {
            "fen": self.board.fen(),
            "board": self._board_to_array(),
            "move_stack_san": list(self._move_stack_san),
        }

    def get_fen(self) -> str:
        return self.board.fen()

    def _board_to_array(self) -> list[list[Optional[str]]]:
        """
        Return 8x8 array (rank 8 → rank 1).
        Each cell is e.g. "wP", "bK", or null.
        """
        rows: list[list[Optional[str]]] = []
        for rank in range(7, -1, -1):          # rank 8 down to 1
            row: list[Optional[str]] = []
            for file in range(8):              # a–h
                piece = self.board.piece_at(chess.square(file, rank))
                if piece is None:
                    row.append(None)
                else:
                    color = "w" if piece.color == chess.WHITE else "b"
                    row.append(f"{color}{_PIECE_MAP[piece.piece_type].upper()}")
            rows.append(row)
        return rows


class ChessEngine(GameEngine):
    game_type = "chess"
    min_players = 2
    max_players = 2

    def create_initial_state(self) -> ChessState:
        return ChessState()

    def validate_move(self, state: ChessState, move_uci: str) -> bool:
        try:
            m = chess.Move.from_uci(move_uci)
            return m in state.board.legal_moves
        except (ValueError, chess.InvalidMoveError):
            return False

    def apply_move(self, state: ChessState, move_uci: str) -> ChessState:
        new_board = deepcopy(state.board)
        m = chess.Move.from_uci(move_uci)
        san = new_board.san(m)
        new_board.push(m)
        new_san_stack = list(state._move_stack_san) + [san]
        return ChessState(
            board=new_board,
            _last_move_san=san,
            _move_stack_san=new_san_stack,
        )

    def get_legal_moves(self, state: ChessState) -> list[str]:
        return [m.uci() for m in state.board.legal_moves]

    def get_current_turn(self, state: ChessState) -> int:
        """seat 1 = white, seat 2 = black."""
        return 1 if state.board.turn == chess.WHITE else 2

    def is_terminal(self, state: ChessState) -> Optional[dict]:
        b = state.board
        if b.is_checkmate():
            # The side to move is checkmated → the *other* side won
            winner = 2 if b.turn == chess.WHITE else 1
            result_key = "player1_win" if winner == 1 else "player2_win"
            return {"result": result_key, "reason": "checkmate"}
        if b.is_stalemate():
            return {"result": "draw", "reason": "stalemate"}
        if b.is_insufficient_material():
            return {"result": "draw", "reason": "insufficient_material"}
        if b.is_fifty_moves():
            return {"result": "draw", "reason": "fifty_move_rule"}
        if b.is_repetition(3):
            return {"result": "draw", "reason": "threefold_repetition"}
        return None

    def get_player_view(self, state: ChessState, seat: int) -> dict:
        """Chess is perfect information — both players see the full board."""
        d = state.to_dict()
        legal = self.get_legal_moves(state) if self.get_current_turn(state) == seat else []
        d["legal_moves"] = legal
        d["turn_seat"] = self.get_current_turn(state)
        d["is_check"] = state.board.is_check()

        # Last move squares for highlighting
        if state.board.move_stack:
            last = state.board.move_stack[-1]
            d["last_move"] = {
                "from": chess.square_name(last.from_square),
                "to": chess.square_name(last.to_square),
            }
        else:
            d["last_move"] = None

        terminal = self.is_terminal(state)
        d["game_over"] = terminal is not None
        d["result"] = terminal
        return d

    def get_last_move_san(self, state: ChessState) -> Optional[str]:
        return state._last_move_san
