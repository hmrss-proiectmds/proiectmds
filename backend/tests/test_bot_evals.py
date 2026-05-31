"""
Bot evaluation tests.

These tests verify that every AI bot:
  1. Always returns a move that is in the engine's legal-moves list.
  2. Does not crash on any encountered game state.
  3. Falls back gracefully when the HuggingFace model produces garbage output.

HuggingFace bots (PokerBot, MahjongBot) are tested with a mocked pipeline so
the tests run in CI without downloading the model.  The chess bot uses a
different architecture (custom transformer loaded from disk); those tests are
skipped when the model files are absent (e.g. CI).

Shanten heuristic (MahjongBot fallback) is also tested directly.
"""

import random
from unittest.mock import MagicMock, patch

import pytest

from app.games.chess.engine import ChessEngine
from app.games.mahjong.engine import MahjongEngine
from app.games.poker.engine import PokerEngine


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_raise(move: str) -> str:
    """Convert 'RAISE min max' → 'RAISE min' (concrete raise for validate_move)."""
    if move.startswith("RAISE ") and len(move.split()) == 3:
        parts = move.split()
        return f"RAISE {parts[1]}"
    return move


def _mock_pipeline(generated_text: str):
    """Return a mock HF pipeline callable that always generates *generated_text*."""
    mock = MagicMock()
    mock.return_value = [{"generated_text": generated_text}]
    return mock


# ── Random bot ────────────────────────────────────────────────────────────────


class TestRandomBot:
    """Random bot must always return a validated legal move for every game."""

    def test_chess_returns_legal_move(self):
        from app.games.bots.random_bot import pick_random_move

        engine = ChessEngine()
        state = engine.create_initial_state()
        for _ in range(10):
            if engine.is_terminal(state):
                break
            move = pick_random_move(engine, state)
            assert engine.validate_move(state, move), f"Illegal chess move: {move}"
            state = engine.apply_move(state, move)

    def test_poker_returns_legal_move(self):
        from app.games.bots.random_bot import pick_random_move

        engine = PokerEngine()
        state = engine.create_initial_state(num_players=3)
        for _ in range(10):
            if engine.is_terminal(state):
                break
            moves = engine.get_legal_moves(state)
            if not moves:
                break
            move = pick_random_move(engine, state)
            assert engine.validate_move(state, _resolve_raise(move)), f"Illegal poker move: {move}"
            state = engine.apply_move(state, _resolve_raise(move))

    def test_mahjong_returns_legal_move(self):
        from app.games.bots.random_bot import pick_random_move

        engine = MahjongEngine()
        state = engine.create_initial_state()
        for _ in range(20):
            if engine.is_terminal(state):
                break
            moves = engine.get_legal_moves(state)
            if not moves:
                break
            move = pick_random_move(engine, state)
            assert engine.validate_move(state, move), f"Illegal mahjong move: {move}"
            state = engine.apply_move(state, move)

    def test_random_bot_plays_full_mahjong_game(self):
        """Simulate a complete game using only the random bot — must not crash."""
        from app.games.bots.random_bot import pick_random_move

        engine = MahjongEngine()
        state = engine.create_initial_state()
        for _ in range(300):
            if engine.is_terminal(state):
                return
            moves = engine.get_legal_moves(state)
            if not moves:
                return
            state = engine.apply_move(state, pick_random_move(engine, state))
        pytest.fail("Game did not terminate within 300 moves")


# ── Poker HF bot ──────────────────────────────────────────────────────────────


class TestPokerHFBot:
    """HuggingFace Poker bot — tested with mocked pipeline."""

    def _get_state(self):
        engine = PokerEngine()
        return engine, engine.create_initial_state(num_players=3)

    def test_returns_legal_move_on_valid_model_output(self):
        from app.games.bots.hf_pokerbot import pick_hf_poker_move

        engine, state = self._get_state()
        # Simulate model outputting "FOLD"
        mock_pipe = _mock_pipeline("Best action: FOLD now.")
        with patch("app.games.bots.hf_pokerbot._get_pipeline", return_value=mock_pipe):
            move = pick_hf_poker_move(engine, state)
        assert engine.validate_move(state, _resolve_raise(move)), f"Illegal: {move}"

    def test_returns_legal_move_on_garbage_output(self):
        from app.games.bots.hf_pokerbot import pick_hf_poker_move

        engine, state = self._get_state()
        mock_pipe = _mock_pipeline("xyzzy gobbledygook nonsense lemon 999 ???")
        with patch("app.games.bots.hf_pokerbot._get_pipeline", return_value=mock_pipe):
            move = pick_hf_poker_move(engine, state)
        assert engine.validate_move(state, _resolve_raise(move)), f"Illegal after fallback: {move}"

    def test_returns_legal_move_on_empty_output(self):
        from app.games.bots.hf_pokerbot import pick_hf_poker_move

        engine, state = self._get_state()
        mock_pipe = _mock_pipeline("")
        with patch("app.games.bots.hf_pokerbot._get_pipeline", return_value=mock_pipe):
            move = pick_hf_poker_move(engine, state)
        assert engine.validate_move(state, _resolve_raise(move)), f"Illegal after empty output: {move}"

    def test_never_returns_raise_range_string(self):
        """Bot must resolve RAISE to a concrete amount, never return 'RAISE min max'."""
        from app.games.bots.hf_pokerbot import pick_hf_poker_move

        engine, state = self._get_state()
        mock_pipe = _mock_pipeline("RAISE")
        with patch("app.games.bots.hf_pokerbot._get_pipeline", return_value=mock_pipe):
            move = pick_hf_poker_move(engine, state)
        parts = move.split()
        assert not (len(parts) == 3 and parts[0] == "RAISE"), "Returned raw RAISE range"


# ── Mahjong HF bot ────────────────────────────────────────────────────────────


class TestMahjongHFBot:
    """HuggingFace Mahjong bot — tested with mocked pipeline and direct heuristic tests."""

    def _get_state(self):
        engine = MahjongEngine()
        return engine, engine.create_initial_state()

    def test_returns_legal_move_on_garbage_output(self):
        from app.games.bots.hf_mahjongbot import pick_hf_mahjong_move

        engine, state = self._get_state()
        mock_pipe = _mock_pipeline("zzz pqrst 000 invalid text here")
        with patch("app.games.bots.hf_mahjongbot._get_pipeline", return_value=mock_pipe):
            move = pick_hf_mahjong_move(engine, state)
        assert engine.validate_move(state, move), f"Illegal mahjong move: {move}"

    def test_returns_legal_move_on_valid_tile_output(self):
        from app.games.bots.hf_mahjongbot import pick_hf_mahjong_move

        engine, state = self._get_state()
        # Pick a tile that's actually in hand to feed to the model
        hand = state.hands[1]
        tile = hand[0]
        mock_pipe = _mock_pipeline(f"Best discard tile: {tile} yes")
        with patch("app.games.bots.hf_mahjongbot._get_pipeline", return_value=mock_pipe):
            move = pick_hf_mahjong_move(engine, state)
        assert engine.validate_move(state, move), f"Illegal move from valid output: {move}"

    def test_tsumo_taken_immediately_when_winning(self):
        """Bot must declare TSUMO whenever it is legal (winning hand)."""
        from app.games.bots.hf_mahjongbot import pick_hf_mahjong_move
        from app.games.mahjong.engine import MahjongState, is_winning_hand

        engine = MahjongEngine()
        # Build a state where seat 1 has a winning 14-tile hand
        # Bamboo sequence: 1s2s3s 4s5s6s 7s8s9s + pair 1m1m = winning
        winning_hand = [
            "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
            "1m", "1m", "2m", "3m", "4m",
        ]
        assert is_winning_hand(winning_hand), "Test hand must be winning"

        state = engine.create_initial_state()
        state.hands[1] = winning_hand
        state.current_seat = 1

        mock_pipe = _mock_pipeline("some garbage")
        with patch("app.games.bots.hf_mahjongbot._get_pipeline", return_value=mock_pipe):
            move = pick_hf_mahjong_move(engine, state)
        assert move == "TSUMO", f"Expected TSUMO, got: {move}"


# ── Shanten heuristic (MahjongBot fallback) ───────────────────────────────────


class TestShantenHeuristic:
    """Direct tests for _best_shanten_discard — the bot's fallback strategy."""

    def test_returns_a_tile_in_hand(self):
        from app.games.bots.hf_mahjongbot import _best_shanten_discard

        engine = MahjongEngine()
        state = engine.create_initial_state()
        hand = state.hands[1]
        legal_discards = [m for m in engine.get_legal_moves(state) if m.startswith("DISCARD_")]
        assert legal_discards

        tile = _best_shanten_discard(hand, legal_discards)
        assert tile in hand, f"Returned tile '{tile}' not in hand {hand}"

    def test_minimizes_shanten(self):
        """The chosen discard should leave shanten ≤ every other possible discard."""
        from app.games.bots.hf_mahjongbot import _best_shanten_discard
        from app.games.mahjong.engine import shanten

        engine = MahjongEngine()
        # Try several random starting states for robustness
        for _ in range(5):
            state = engine.create_initial_state()
            hand = state.hands[1]
            legal_discards = [m for m in engine.get_legal_moves(state) if m.startswith("DISCARD_")]
            if not legal_discards:
                continue

            best_tile = _best_shanten_discard(hand, legal_discards)
            remaining_best = list(hand)
            remaining_best.remove(best_tile)
            best_sh = shanten(remaining_best)

            for move in legal_discards:
                tile = move[8:]
                remaining = list(hand)
                remaining.remove(tile)
                sh = shanten(remaining)
                assert sh >= best_sh, (
                    f"Tile {tile} gives shanten {sh} < best {best_sh} "
                    f"(best_tile={best_tile})"
                )

    def test_handles_single_discard_option(self):
        """Should not crash when only one legal discard is available."""
        from app.games.bots.hf_mahjongbot import _best_shanten_discard

        hand = ["1m"] * 14
        legal_discards = ["DISCARD_1m"]
        tile = _best_shanten_discard(hand, legal_discards)
        assert tile == "1m"


# ── Chess HF bot (model-dependent) ───────────────────────────────────────────


class TestChessHFBot:
    """Tests for the chess bot — skipped when model files are not present."""

    @pytest.fixture(autouse=True)
    def skip_if_no_model(self):
        from app.games.bots.hf_chessbot import is_available

        if not is_available():
            pytest.skip("ChessBot model not downloaded — run download_model.py first")

    def test_returns_legal_move(self):
        from app.games.bots.hf_chessbot import pick_hf_move

        engine = ChessEngine()
        state = engine.create_initial_state()
        move = pick_hf_move(engine, state)
        assert engine.validate_move(state, move), f"Illegal chess bot move: {move}"

    def test_returns_legal_move_mid_game(self):
        from app.games.bots.hf_chessbot import pick_hf_move
        from app.games.bots.random_bot import pick_random_move

        engine = ChessEngine()
        state = engine.create_initial_state()
        # Advance 10 half-moves with the random bot to get a mid-game position
        for _ in range(10):
            if engine.is_terminal(state):
                break
            state = engine.apply_move(state, pick_random_move(engine, state))

        if not engine.is_terminal(state):
            move = pick_hf_move(engine, state)
            assert engine.validate_move(state, move), f"Illegal mid-game move: {move}"

    def test_fallback_on_illegal_model_output(self):
        """When the model returns an illegal UCI string, fallback must give a legal move."""
        from app.games.bots.hf_chessbot import pick_hf_move

        engine = ChessEngine()
        state = engine.create_initial_state()

        class _BadModel:
            def get_move_from_fen_no_thinking(self, fen, T, device, force_legal):
                return "e1e8"  # always illegal

        with patch("app.games.bots.hf_chessbot._load_model", return_value=(_BadModel(), "cpu")):
            move = pick_hf_move(engine, state)
        assert engine.validate_move(state, move), f"Fallback returned illegal move: {move}"
