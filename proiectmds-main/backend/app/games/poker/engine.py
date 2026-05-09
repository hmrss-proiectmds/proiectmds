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
from texasholdem.game.player_state import PlayerState

from app.games.base import GameEngine, GameState

# Map our user-facing action names (no underscore) to the library's ActionType enum
_ACTION_MAP = {
    "FOLD": ActionType.FOLD,
    "CHECK": ActionType.CHECK,
    "CALL": ActionType.CALL,
    "ALLIN": ActionType.ALL_IN,
    "RAISE": ActionType.RAISE,
}

# ── Card rendering helpers ──
_SUIT_SYMBOLS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
_RANK_COLORS = {"♥": "red", "♦": "red", "♠": "black", "♣": "black"}


def _card_str(card) -> str:
    """Convert a texasholdem Card to a human-readable string like 'A♠'."""
    raw = str(card)                     # e.g. 'As', 'Td', '2c'
    rank = raw[:-1]                     # 'A', 'T', '2'
    suit_char = raw[-1]                 # 's', 'h', 'd', 'c'
    return f"{rank}{_SUIT_SYMBOLS.get(suit_char, suit_char)}"


def _hand_rank_name(rank: int) -> str:
    """Convert a texasholdem numeric hand rank to a human-readable name."""
    if rank <= 1:    return "Royal Flush"
    if rank <= 10:   return "Straight Flush"
    if rank <= 166:  return "Four of a Kind"
    if rank <= 322:  return "Full House"
    if rank <= 1599: return "Flush"
    if rank <= 1609: return "Straight"
    if rank <= 2467: return "Three of a Kind"
    if rank <= 3325: return "Two Pair"
    if rank <= 6185: return "Pair"
    return "High Card"


# ── Hand phase names ──
_VALID_PHASES = {"PREFLOP", "FLOP", "TURN", "RIVER", "SETTLE"}

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
    _hand_number: int = field(default=1, repr=False)
    _hand_just_ended: bool = field(default=False, repr=False)
    _showdown_info: Optional[dict] = field(default=None, repr=False)

    # ── GameState interface ──

    def to_dict(self) -> dict:
        # Determine hand phase
        phase = "WAITING"
        if self.game.is_hand_running():
            try:
                name = self.game.hand_phase.name
                phase = name if name in _VALID_PHASES else "PREFLOP"
            except Exception:
                phase = "PREFLOP"
        elif self._hand_just_ended:
            phase = "SHOWDOWN"

        return {
            "num_players": self.num_players,
            "board": [_card_str(c) for c in self.game.board],
            "pot": sum(p.get_total_amount() for p in self.game.pots),
            "current_player": self.game.current_player,
            "is_hand_running": self.game.is_hand_running(),
            "is_game_running": self.game.is_game_running(),
            "action_log": list(self._action_log[-20:]),
            "turn_number": self._turn_number,
            "hand_number": self._hand_number,
            "hand_phase": phase,
            "hand_just_ended": self._hand_just_ended,
            "showdown_info": self._showdown_info,
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
        return PokerState(game=game, num_players=num, _hand_number=1)

    # ── Move format ──
    # "FOLD", "CHECK", "CALL", "ALLIN", "RAISE <amount>"

    def validate_move(self, state: PokerState, move: str) -> bool:
        parts = move.strip().upper().split()
        if not parts:
            return False
        action_type = _ACTION_MAP.get(parts[0])
        if action_type is None:
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
        action_type = _ACTION_MAP[parts[0]]
        val = int(parts[1]) if len(parts) > 1 else None

        new_game = copy.deepcopy(state.game)
        player_id = new_game.current_player
        new_game.take_action(action_type, val)

        # Build log entry — use ALLIN (no underscore, no space) for easy parsing
        action_label = parts[0]
        if val is not None:
            action_label += f" ${val}"
        log_entry = f"Seat {player_id + 1}: {action_label}"

        new_log = list(state._action_log) + [log_entry]
        new_turn = state._turn_number + 1

        # Check if the hand just ended (but DON'T auto-start the next one —
        # let the AI loop handle the pause so players can see the results)
        hand_just_ended = (
            not new_game.is_hand_running() and new_game.is_game_running()
        )

        # ── Extract showdown info when hand ends ──
        showdown_info = None
        if hand_just_ended:
            showdown_info = self._extract_showdown(new_game, new_log)

        return PokerState(
            game=new_game,
            num_players=state.num_players,
            _last_action=log_entry,
            _action_log=new_log,
            _turn_number=new_turn,
            _hand_number=state._hand_number,
            _hand_just_ended=hand_just_ended,
            _showdown_info=showdown_info,
        )

    @staticmethod
    def _extract_showdown(game: TexasHoldEm, log: list[str]) -> dict | None:
        """Extract winner info from hand_history after a hand ends."""
        try:
            hh = game.hand_history
            if not hh or not hh.settle:
                return None

            pot_winners = hh.settle.pot_winners  # {pot_id: (amount, hand_rank, [winner_ids])}
            if not pot_winners:
                return None

            # Collect all winners across pots
            winners = []
            for pot_id, (amount, hand_rank, winner_ids) in pot_winners.items():
                for wid in winner_ids:
                    hand_cards = game.hands.get(wid, [])
                    hand_name = _hand_rank_name(hand_rank)
                    winners.append({
                        "seat": wid + 1,  # 1-indexed
                        "cards": [_card_str(c) for c in hand_cards],
                        "hand_name": hand_name,
                        "amount_won": amount // len(winner_ids),
                    })

            if not winners:
                return None

            # Add showdown log entries
            for w in winners:
                entry = f"🏆 Seat {w['seat']} wins ${w['amount_won']} with {w['hand_name']} ({', '.join(w['cards'])})"
                log.append(entry)

            # Also reveal all hands that went to showdown (non-folded)
            revealed_hands = {}
            for pid, cards in game.hands.items():
                revealed_hands[pid + 1] = [_card_str(c) for c in cards]  # seat (1-indexed)

            return {
                "winners": winners,
                "revealed_hands": revealed_hands,
            }
        except Exception:
            return None

    def needs_new_hand(self, state: PokerState) -> bool:
        """Check if a new hand needs to be started."""
        return state._hand_just_ended

    def start_next_hand(self, state: PokerState) -> PokerState:
        """Start the next hand — clears the action log and increments hand number."""
        new_game = copy.deepcopy(state.game)
        new_hand = state._hand_number + 1

        # Reset log for the new hand, add a separator
        new_log = [f"━━━ Hand #{new_hand} ━━━"]

        new_game.start_hand()

        return PokerState(
            game=new_game,
            num_players=state.num_players,
            _last_action=None,
            _action_log=new_log,
            _turn_number=state._turn_number,
            _hand_number=new_hand,
            _hand_just_ended=False,
        )

    def get_legal_moves(self, state: PokerState) -> list[str]:
        if not state.game.is_hand_running():
            return []

        pid = state.game.current_player
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

        # The texasholdem library's get_available_moves() has a bug where it
        # doesn't list CALL or ALL_IN for short-stacked players who can't
        # afford the full bet, even though validate_move() accepts them.
        # Manually probe for these critical actions to ensure no player is
        # forced to fold when they could go all-in.
        for action_type in (ActionType.CALL, ActionType.ALL_IN, ActionType.CHECK):
            if action_type.name not in valid_actions:
                try:
                    if state.game.validate_move(pid, action_type):
                        valid_actions.add(action_type.name)
                except Exception:
                    pass

        result = []
        if "FOLD" in valid_actions:
            result.append("FOLD")
        if "CHECK" in valid_actions:
            result.append("CHECK")
        if "CALL" in valid_actions:
            result.append("CALL")
        if "ALL_IN" in valid_actions:
            result.append("ALLIN")
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
        _ACTIVE_STATES = {PlayerState.IN, PlayerState.TO_CALL, PlayerState.ALL_IN}
        chips_info = []
        for i, p in enumerate(state.game.players):
            chips_info.append({
                "seat": i + 1,
                "chips": p.chips,
                "is_active": p.state in _ACTIVE_STATES,
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
