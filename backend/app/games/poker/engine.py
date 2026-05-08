"""
Poker (Texas Hold'em) game engine powered by the texasholdem library.
Supports 3–7 players, wraps the library into the platform's GameEngine interface.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

from texasholdem import TexasHoldEm
from texasholdem.game.action_type import ActionType

from app.games.base import GameEngine, GameState

# ── Card rendering helpers ──
_SUIT_SYMBOLS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
_RANK_COLORS = {"♥": "red", "♦": "red", "♠": "black", "♣": "black"}


def _card_str(card) -> str:
    """Convert a texasholdem Card to a human-readable string like 'A♠'."""
    raw = str(card)                     # e.g. 'As', 'Td', '2c'
    rank = raw[:-1]                     # 'A', 'T', '2'
    suit_char = raw[-1]                 # 's', 'h', 'd', 'c'
    return f"{rank}{_SUIT_SYMBOLS.get(suit_char, suit_char)}"


# ── State ──

@dataclass
class PokerState(GameState):
    """Wraps a TexasHoldEm game object as our GameState."""

    game: TexasHoldEm = field(default_factory=lambda: TexasHoldEm(
        buyin=500, big_blind=10, small_blind=5, max_players=6
    ))
    num_players: int = 6
    _last_action: Optional[str] = field(default=None, repr=False)
    _action_log: list[str] = field(default_factory=list, repr=False)
    _turn_number: int = field(default=0, repr=False)

    # ── GameState interface ──

    def to_dict(self) -> dict:
        return {
            "num_players": self.num_players,
            "board": [_card_str(c) for c in self.game.board],
            "pot": sum(p.get_total_amount() for p in self.game.pots),
            "current_player": self.game.current_player,
            "is_hand_running": self.game.is_hand_running(),
            "is_game_running": self.game.is_game_running(),
            "action_log": list(self._action_log[-20:]),
            "turn_number": self._turn_number,
        }

    def get_fen(self) -> str:
        board_str = ",".join(_card_str(c) for c in self.game.board)
        return f"poker|board={board_str}|turn={self._turn_number}"


# ── Engine ──

class PokerEngine(GameEngine):
    game_type = "poker"
    min_players = 3
    max_players = 7

    def create_initial_state(self, num_players: int = 6) -> PokerState:
        """Create a new poker game for `num_players` (3-7)."""
        num = max(3, min(7, num_players))
        game = TexasHoldEm(buyin=500, big_blind=10, small_blind=5, max_players=num)
        game.start_hand()
        return PokerState(game=game, num_players=num)

    # ── Move format ──
    # "FOLD", "CHECK", "CALL", "ALL_IN", "RAISE <amount>"

    def validate_move(self, state: PokerState, move: str) -> bool:
        parts = move.strip().upper().split()
        if not parts:
            return False
        try:
            action_type = ActionType[parts[0]]
        except KeyError:
            return False

        val = None
        if action_type == ActionType.RAISE:
            if len(parts) < 2:
                return False
            try:
                val = int(parts[1])
            except ValueError:
                return False

        try:
            return state.game.validate_move(state.game.current_player, action_type, val)
        except Exception:
            return False

    def apply_move(self, state: PokerState, move: str) -> PokerState:
        parts = move.strip().upper().split()
        action_type = ActionType[parts[0]]
        val = int(parts[1]) if len(parts) > 1 else None

        new_game = copy.deepcopy(state.game)
        player_id = new_game.current_player
        new_game.take_action(action_type, val)

        # Build log entry
        action_desc = parts[0]
        if val is not None:
            action_desc += f" ${val}"
        log_entry = f"Seat {player_id + 1}: {action_desc}"

        new_log = list(state._action_log) + [log_entry]
        new_turn = state._turn_number + 1

        # If the hand ended but game continues, start next hand
        if not new_game.is_hand_running() and new_game.is_game_running():
            new_game.start_hand()

        return PokerState(
            game=new_game,
            num_players=state.num_players,
            _last_action=log_entry,
            _action_log=new_log,
            _turn_number=new_turn,
        )

    def get_legal_moves(self, state: PokerState) -> list[str]:
        if not state.game.is_hand_running():
            return []

        moves_iter = state.game.get_available_moves()
        valid_actions: set[str] = set()
        min_raise = None
        max_raise = None

        for action, val in moves_iter:
            if action == ActionType.RAISE:
                if min_raise is None or val < min_raise:
                    min_raise = val
                if max_raise is None or val > max_raise:
                    max_raise = val
            else:
                valid_actions.add(action.name)

        result = []
        if "FOLD" in valid_actions:
            result.append("FOLD")
        if "CHECK" in valid_actions:
            result.append("CHECK")
        if "CALL" in valid_actions:
            result.append("CALL")
        if "ALL_IN" in valid_actions:
            result.append("ALL_IN")
        if min_raise is not None:
            result.append(f"RAISE {min_raise} {max_raise}")
        return result

    def get_current_turn(self, state: PokerState) -> int:
        """Seats are 1-indexed.  texasholdem player ids are 0-indexed."""
        if not state.game.is_hand_running():
            return 1  # doesn't matter when hand isn't running
        return state.game.current_player + 1

    def is_terminal(self, state: PokerState) -> Optional[dict]:
        if state.game.is_game_running():
            return None

        # Game over — find who has the most chips
        best_chips = -1
        winner_seat = -1
        for i, p in enumerate(state.game.players):
            if p.chips > best_chips:
                best_chips = p.chips
                winner_seat = i + 1  # 1-indexed

        return {
            "result": f"player{winner_seat}_win",
            "reason": "last_player_standing",
            "winner_seat": winner_seat,
        }

    def get_player_view(self, state: PokerState, seat: int) -> dict:
        """Return per-player view of the game.  seat is 1-indexed."""
        d = state.to_dict()
        pid = seat - 1  # 0-indexed player id

        # Your hand (hidden from others)
        my_hand = state.game.hands.get(pid, [])
        d["your_hand"] = [_card_str(c) for c in my_hand]

        # Chips for all players
        chips_info = []
        for i, p in enumerate(state.game.players):
            chips_info.append({
                "seat": i + 1,
                "chips": p.chips,
                "is_active": i in state.game.hands,
            })
        d["chips"] = chips_info

        # Your specific chip count
        d["your_chips"] = state.game.players[pid].chips if pid < len(state.game.players) else 0

        # Turn info
        is_my_turn = (self.get_current_turn(state) == seat) and state.game.is_hand_running()
        d["legal_moves"] = self.get_legal_moves(state) if is_my_turn else []
        d["turn_seat"] = self.get_current_turn(state)

        # Bet-to-call for the current player
        if state.game.is_hand_running():
            d["chips_to_call"] = state.game.chips_to_call(state.game.current_player)
        else:
            d["chips_to_call"] = 0

        # Terminal
        terminal = self.is_terminal(state)
        d["game_over"] = terminal is not None
        d["result"] = terminal

        return d

    def get_last_move_san(self, state: PokerState) -> Optional[str]:
        return state._last_action
