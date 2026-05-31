"""
Riichi Mahjong game engine — 4 players, simplified Japanese rules.

Supported:
  - Full draw/discard turn loop
  - Tsumo (win by self-draw)
  - Ron (auto-awarded when another player's discard completes any opponent's hand)
  - Riichi declaration (tenpai + commitment; riichi players may only discard the drawn tile)
  - Ryuukyoku (exhaustive draw when wall is empty)

Not implemented (out of scope for v1):
  - Pon / Chi / Kan calls
  - Dora indicators
  - Han/fu scoring (ELO is used instead)
  - Multiple rounds / honba counters
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Optional

from app.games.base import GameEngine, GameState

# ── Tile definitions ──────────────────────────────────────────────────────────

_MAN   = [f"{n}m" for n in range(1, 10)]   # 1m–9m  (characters)
_PIN   = [f"{n}p" for n in range(1, 10)]   # 1p–9p  (circles)
_SOU   = [f"{n}s" for n in range(1, 10)]   # 1s–9s  (bamboo)
_HONOR = [f"{n}z" for n in range(1, 8)]    # 1z–7z  (winds 1-4, dragons 5-7)

ALL_34: list[str] = _MAN + _PIN + _SOU + _HONOR          # 34 unique tile types
FULL_WALL: list[str] = [t for t in ALL_34 for _ in range(4)]  # 136 tiles

# Human-readable display strings
_DISPLAY: dict[str, str] = {
    **{f"{n}m": f"{n}m" for n in range(1, 10)},
    **{f"{n}p": f"{n}p" for n in range(1, 10)},
    **{f"{n}s": f"{n}s" for n in range(1, 10)},
    "1z": "East", "2z": "South", "3z": "West", "4z": "North",
    "5z": "Haku", "6z": "Hatsu", "7z": "Chun",
}

# Suit label for frontend colouring
TILE_SUIT: dict[str, str] = {
    **{f"{n}m": "man"    for n in range(1, 10)},
    **{f"{n}p": "pin"    for n in range(1, 10)},
    **{f"{n}s": "sou"    for n in range(1, 10)},
    **{f"{n}z": "honor"  for n in range(1, 8)},
}

def tile_display(tile: str) -> str:
    return _DISPLAY.get(tile, tile)


# ── Tile ↔ index helpers ──────────────────────────────────────────────────────

def tile_to_34(tile: str) -> int:
    """Return 0-based index in the 34-tile type space."""
    n = int(tile[0])
    s = tile[1]
    if s == 'm': return n - 1
    if s == 'p': return 9  + n - 1
    if s == 's': return 18 + n - 1
    if s == 'z': return 27 + n - 1
    raise ValueError(f"Unknown tile: {tile}")


def hand_to_34_counts(tiles: list[str]) -> list[int]:
    counts = [0] * 34
    for t in tiles:
        counts[tile_to_34(t)] += 1
    return counts


# ── Win / tenpai detection ────────────────────────────────────────────────────

def is_winning_hand(tiles: list[str]) -> bool:
    """Return True if *tiles* (exactly 14) form a complete winning hand."""
    if len(tiles) != 14:
        return False
    try:
        from mahjong.agari import Agari
        return bool(Agari().is_agari(hand_to_34_counts(tiles)))
    except Exception:
        return False


def shanten(tiles_13: list[str]) -> int:
    """
    Shanten number for a 13-tile hand.
    -1 = winning, 0 = tenpai, N = N tiles away from tenpai.
    """
    if len(tiles_13) < 13:
        return 8
    try:
        from mahjong.shanten import Shanten
        return Shanten().calculate_shanten(hand_to_34_counts(tiles_13[:13]))
    except Exception:
        return 8


def riichi_candidates(hand_14: list[str], already_riichi: bool) -> list[str]:
    """Tiles in *hand_14* whose removal leaves the hand at tenpai (shanten=0)."""
    if already_riichi:
        return []
    result = []
    for tile in sorted(set(hand_14)):
        remaining = list(hand_14)
        remaining.remove(tile)
        if shanten(remaining) == 0:
            result.append(tile)
    return result


# ── State ─────────────────────────────────────────────────────────────────────

@dataclass
class MahjongState(GameState):
    wall: list[str]                    = field(default_factory=list)
    hands: dict[int, list[str]]        = field(default_factory=dict)   # seat→tiles
    discards: dict[int, list[str]]     = field(default_factory=dict)   # seat→pile
    current_seat: int                  = 1
    riichi_declared: dict[int, bool]   = field(default_factory=dict)
    last_drawn: dict[int, Optional[str]] = field(default_factory=dict) # seat→tile
    last_discard: Optional[str]        = None
    last_discard_seat: Optional[int]   = None
    winner_seat: Optional[int]         = None
    win_type: Optional[str]            = None   # "tsumo"|"ron"|"ryuukyoku"
    _turn_number: int                  = 0
    _last_action: Optional[str]        = None

    # ── GameState interface ──

    def to_dict(self) -> dict:
        return {
            "hands":             {str(s): sorted(h) for s, h in self.hands.items()},
            "discards":          {str(s): list(d)   for s, d in self.discards.items()},
            "current_seat":      self.current_seat,
            "riichi":            {str(s): v for s, v in self.riichi_declared.items()},
            "last_discard":      self.last_discard,
            "last_discard_seat": self.last_discard_seat,
            "wall_remaining":    len(self.wall),
            "winner_seat":       self.winner_seat,
            "win_type":          self.win_type,
            "_turn_number":      self._turn_number,
            "_last_action":      self._last_action,
        }

    def get_fen(self) -> str:
        hands_str = "|".join(
            ",".join(sorted(self.hands.get(s, []))) for s in range(1, 5)
        )
        return f"mj:{self.current_seat}:{hands_str}"


# ── Engine ────────────────────────────────────────────────────────────────────

class MahjongEngine(GameEngine):
    game_type   = "mahjong"
    min_players = 4
    max_players = 4

    # ── Initialisation ──

    def create_initial_state(self) -> MahjongState:
        wall = list(FULL_WALL)
        random.shuffle(wall)

        hands: dict[int, list[str]] = {}
        for seat in range(1, 5):
            hands[seat] = [wall.pop() for _ in range(13)]

        # Seat 1 draws the opening tile
        drawn = wall.pop()
        hands[1].append(drawn)

        return MahjongState(
            wall             = wall,
            hands            = hands,
            discards         = {s: [] for s in range(1, 5)},
            current_seat     = 1,
            riichi_declared  = {s: False for s in range(1, 5)},
            last_drawn       = {s: None  for s in range(1, 5)},
            last_discard     = None,
            last_discard_seat= None,
            winner_seat      = None,
            win_type         = None,
            _turn_number     = 0,
            _last_action     = None,
        )

    # ── Move enumeration ──

    def get_legal_moves(self, state: MahjongState) -> list[str]:
        seat = state.current_seat
        hand = state.hands.get(seat, [])

        if len(hand) != 14 or state.winner_seat is not None or state.win_type:
            return []

        moves: list[str] = []
        in_riichi = state.riichi_declared.get(seat, False)

        # Tsumo always takes priority
        if is_winning_hand(hand):
            moves.append("TSUMO")

        if in_riichi:
            # Riichi players must discard the drawn tile (unless they just won)
            drawn = state.last_drawn.get(seat)
            if drawn and drawn in hand and "TSUMO" not in moves:
                moves.append(f"DISCARD_{drawn}")
            elif "TSUMO" not in moves:
                # Safety fallback — discard last tile
                moves.append(f"DISCARD_{hand[-1]}")
        else:
            # Riichi declarations
            for tile in riichi_candidates(hand, in_riichi):
                moves.append(f"RIICHI_{tile}")
            # Regular discards (deduplicated, sorted)
            for tile in sorted(set(hand)):
                moves.append(f"DISCARD_{tile}")

        return moves

    def validate_move(self, state: MahjongState, move: str) -> bool:
        return move in self.get_legal_moves(state)

    # ── Move application ──

    def apply_move(self, state: MahjongState, move: str) -> MahjongState:
        s = copy.deepcopy(state)
        seat = s.current_seat
        s._turn_number += 1

        # ── Tsumo ──
        if move == "TSUMO":
            s.winner_seat  = seat
            s.win_type     = "tsumo"
            s._last_action = f"Seat {seat} wins by Tsumo!"
            return s

        # ── Discard / Riichi ──
        declaring_riichi = move.startswith("RIICHI_")
        if declaring_riichi:
            tile = move[7:]
        elif move.startswith("DISCARD_"):
            tile = move[8:]
        else:
            raise ValueError(f"Unknown move: {move!r}")

        if tile not in s.hands[seat]:
            raise ValueError(f"Tile {tile!r} not in hand of seat {seat}")

        s.hands[seat].remove(tile)
        s.discards[seat].append(tile)
        s.last_discard      = tile
        s.last_discard_seat = seat

        if declaring_riichi:
            s.riichi_declared[seat] = True
            s._last_action = f"Seat {seat} RIICHI — discarded {tile_display(tile)}"
        else:
            s._last_action = f"Seat {seat} discarded {tile_display(tile)}"

        # ── Auto-ron check (priority: next player in turn order) ──
        for offset in range(1, 4):
            ron_seat = (seat % 4) + 1 if offset == 1 else ((seat + offset - 1) % 4) + 1
            if is_winning_hand(s.hands[ron_seat] + [tile]):
                s.winner_seat  = ron_seat
                s.win_type     = "ron"
                s._last_action = (
                    f"Seat {ron_seat} wins by Ron on {tile_display(tile)}!"
                )
                return s

        # ── Advance to next player ──
        next_seat = (seat % 4) + 1
        if not s.wall:
            s.win_type     = "ryuukyoku"
            s._last_action = "Wall exhausted — Ryuukyoku (draw)"
            return s

        drawn = s.wall.pop()
        s.hands[next_seat].append(drawn)
        s.last_drawn[next_seat] = drawn
        s.current_seat = next_seat
        return s

    # ── Current turn ──

    def get_current_turn(self, state: MahjongState) -> int:
        return state.current_seat

    # ── Terminal detection ──

    def is_terminal(self, state: MahjongState) -> Optional[dict]:
        if state.winner_seat is not None:
            return {
                "result":      f"player{state.winner_seat}_win",
                "reason":      state.win_type or "win",
                "winner_seat": state.winner_seat,
            }
        if state.win_type == "ryuukyoku":
            return {
                "result":      "draw",
                "reason":      "ryuukyoku",
                "winner_seat": None,
            }
        return None

    # ── Player view (hides opponents' hands) ──

    def get_player_view(self, state: MahjongState, seat: int) -> dict:
        legal = self.get_legal_moves(state) if state.current_seat == seat else []
        return {
            "your_hand":        sorted(state.hands.get(seat, [])),
            "discards":         {str(s): list(d) for s, d in state.discards.items()},
            "other_players":    {
                str(s): {
                    "count":  len(h),
                    "riichi": state.riichi_declared.get(s, False),
                }
                for s, h in state.hands.items() if s != seat
            },
            "current_seat":     state.current_seat,
            "turn_seat":        state.current_seat,
            "riichi":           {str(s): v for s, v in state.riichi_declared.items()},
            "last_discard":     state.last_discard,
            "last_discard_seat":state.last_discard_seat,
            "wall_remaining":   len(state.wall),
            "winner_seat":      state.winner_seat,
            "win_type":         state.win_type,
            "_turn_number":     state._turn_number,
            "_last_action":     state._last_action,
            "legal_moves":      legal,
            "game_over":        state.winner_seat is not None or state.win_type == "ryuukyoku",
        }

    def get_last_move_san(self, state: MahjongState) -> Optional[str]:
        return state._last_action
