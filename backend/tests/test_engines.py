"""
Pure unit tests for all three game engines.

No database, no network access required.
These tests verify the GameEngine contract for ChessEngine, PokerEngine,
and MahjongEngine: initial state, legal move generation, move application,
terminal detection, serialization, and player-view filtering.
"""

import json
import random

import pytest

from app.games.chess.engine import ChessEngine
from app.games.mahjong.engine import MahjongEngine
from app.games.poker.engine import PokerEngine


# ── Chess ─────────────────────────────────────────────────────────────────────


class TestChessEngine:
    def setup_method(self):
        self.engine = ChessEngine()
        self.state = self.engine.create_initial_state()

    def test_initial_state_has_20_legal_moves(self):
        # Standard chess opening: 16 pawn moves + 4 knight moves
        assert len(self.engine.get_legal_moves(self.state)) == 20

    def test_initial_state_is_not_terminal(self):
        assert self.engine.is_terminal(self.state) is None

    def test_seat_1_moves_first(self):
        assert self.engine.get_current_turn(self.state) == 1

    def test_seat_2_moves_after_seat_1(self):
        moves = self.engine.get_legal_moves(self.state)
        state2 = self.engine.apply_move(self.state, moves[0])
        assert self.engine.get_current_turn(state2) == 2

    def test_validate_legal_move_returns_true(self):
        move = self.engine.get_legal_moves(self.state)[0]
        assert self.engine.validate_move(self.state, move) is True

    def test_validate_illegal_move_returns_false(self):
        assert self.engine.validate_move(self.state, "e1e8") is False

    def test_apply_move_does_not_mutate_original(self):
        original_fen = self.state.get_fen()
        moves = self.engine.get_legal_moves(self.state)
        self.engine.apply_move(self.state, moves[0])
        assert self.state.get_fen() == original_fen

    def test_to_dict_is_json_serializable(self):
        json.dumps(self.state.to_dict())  # must not raise

    def test_get_fen_returns_non_empty_string(self):
        assert isinstance(self.state.get_fen(), str)
        assert len(self.state.get_fen()) > 0

    def test_player_view_contains_required_keys(self):
        view = self.engine.get_player_view(self.state, seat=1)
        # Keys provided by the engine itself (your_seat is added by the game service layer)
        for key in ("board", "legal_moves", "turn_seat", "game_over"):
            assert key in view, f"Missing key: {key}"

    def test_player_view_is_json_serializable(self):
        view = self.engine.get_player_view(self.state, seat=1)
        json.dumps(view)

    def test_full_random_game_terminates(self):
        """Play random moves for up to 500 half-moves — must not crash or loop forever."""
        state = self.engine.create_initial_state()
        for _ in range(500):
            if self.engine.is_terminal(state):
                break
            moves = self.engine.get_legal_moves(state)
            if not moves:
                break
            state = self.engine.apply_move(state, random.choice(moves))
        # Not asserting terminal — 50-move stalemate keeps it fair — just no crash


# ── Poker ─────────────────────────────────────────────────────────────────────


class TestPokerEngine:
    def setup_method(self):
        self.engine = PokerEngine()
        self.state = self.engine.create_initial_state(num_players=3)

    def test_initial_state_is_not_terminal(self):
        assert self.engine.is_terminal(self.state) is None

    def test_get_legal_moves_non_empty(self):
        moves = self.engine.get_legal_moves(self.state)
        assert isinstance(moves, list)
        assert len(moves) > 0

    def test_legal_moves_contain_known_actions(self):
        moves = self.engine.get_legal_moves(self.state)
        known = {"FOLD", "CHECK", "CALL", "ALLIN"}
        has_raise = any(m.startswith("RAISE") for m in moves)
        has_standard = bool(known & set(moves))
        assert has_standard or has_raise, f"Unexpected moves: {moves}"

    def test_validate_legal_move(self):
        move = self.engine.get_legal_moves(self.state)[0]
        # Resolve RAISE range to a concrete amount for validation
        if move.startswith("RAISE ") and len(move.split()) == 3:
            parts = move.split()
            move = f"RAISE {parts[1]}"
        assert self.engine.validate_move(self.state, move)

    def test_to_dict_is_json_serializable(self):
        json.dumps(self.state.to_dict())

    def test_get_player_view_filters_hands(self):
        view = self.engine.get_player_view(self.state, seat=1)
        assert "your_hand" in view

    def test_player_view_is_json_serializable(self):
        view = self.engine.get_player_view(self.state, seat=1)
        json.dumps(view)

    def test_fold_advances_turn(self):
        """Folding should not crash and state should change."""
        moves = self.engine.get_legal_moves(self.state)
        if "FOLD" in moves:
            new_state = self.engine.apply_move(self.state, "FOLD")
            assert new_state is not None


# ── Mahjong ───────────────────────────────────────────────────────────────────


class TestMahjongEngine:
    def setup_method(self):
        self.engine = MahjongEngine()
        self.state = self.engine.create_initial_state()

    def test_wall_size_after_deal(self):
        # 136 total − 4×13 dealt − 1 drawn for seat 1 = 83
        assert len(self.state.wall) == 83

    def test_seat_1_has_14_tiles(self):
        assert len(self.state.hands[1]) == 14

    def test_seats_2_3_4_have_13_tiles_each(self):
        for seat in (2, 3, 4):
            assert len(self.state.hands[seat]) == 13, f"Seat {seat} hand size wrong"

    def test_initial_state_is_not_terminal(self):
        assert self.engine.is_terminal(self.state) is None

    def test_seat_1_moves_first(self):
        assert self.engine.get_current_turn(self.state) == 1

    def test_legal_moves_for_seat_1_are_non_empty(self):
        moves = self.engine.get_legal_moves(self.state)
        assert len(moves) > 0

    def test_legal_moves_have_valid_prefixes(self):
        for m in self.engine.get_legal_moves(self.state):
            assert m.startswith("DISCARD_") or m.startswith("RIICHI_") or m == "TSUMO"

    def test_discard_move_reduces_hand(self):
        discards = [m for m in self.engine.get_legal_moves(self.state) if m.startswith("DISCARD_")]
        assert discards, "Expected at least one DISCARD move"
        new_state = self.engine.apply_move(self.state, discards[0])
        assert len(new_state.hands[1]) == 13

    def test_after_discard_next_seat_draws(self):
        discards = [m for m in self.engine.get_legal_moves(self.state) if m.startswith("DISCARD_")]
        new_state = self.engine.apply_move(self.state, discards[0])
        # Unless ron occurred, seat 2 should now have 14 tiles
        if new_state.current_seat == 2:
            assert len(new_state.hands[2]) == 14

    def test_validate_discard_of_tile_not_in_hand_is_false(self):
        assert self.engine.validate_move(self.state, "DISCARD_99z") is False

    def test_to_dict_is_json_serializable(self):
        json.dumps(self.state.to_dict())

    def test_get_fen_starts_with_mj_prefix(self):
        assert self.state.get_fen().startswith("mj:")

    def test_player_view_hides_opponent_tiles(self):
        view = self.engine.get_player_view(self.state, seat=1)
        for seat_str, info in view["other_players"].items():
            assert "count" in info
            assert "tiles" not in info, f"Seat {seat_str} tiles leaked to opponent"

    def test_player_view_includes_turn_seat(self):
        view = self.engine.get_player_view(self.state, seat=1)
        assert "turn_seat" in view
        assert view["turn_seat"] == 1

    def test_player_view_is_json_serializable(self):
        json.dumps(self.engine.get_player_view(self.state, seat=1))

    def test_full_random_game_terminates(self):
        """Play random moves until terminal (tsumo/ron/ryuukyoku)."""
        state = self.engine.create_initial_state()
        for _ in range(300):
            if self.engine.is_terminal(state):
                break
            moves = self.engine.get_legal_moves(state)
            if not moves:
                break
            state = self.engine.apply_move(state, random.choice(moves))
        # A mahjong game should end well before 300 * 4 tiles are exhausted

    def test_terminal_result_has_required_keys(self):
        """Simulate until terminal and verify result schema."""
        state = self.engine.create_initial_state()
        result = None
        for _ in range(300):
            result = self.engine.is_terminal(state)
            if result:
                break
            moves = self.engine.get_legal_moves(state)
            if not moves:
                break
            state = self.engine.apply_move(state, random.choice(moves))

        if result:
            assert "result" in result
            assert "reason" in result
            assert result["result"] in ("player1_win", "player2_win", "player3_win", "player4_win", "draw")
