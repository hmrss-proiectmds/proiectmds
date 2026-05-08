"""
Pydantic schemas for game-related endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Requests ──


class CreateGameRequest(BaseModel):
    game_type: str = "chess"
    vs_ai: bool = False
    bot_type: str = Field("random", description="Bot type: 'random' or 'chessbot'")


class MakeMoveRequest(BaseModel):
    move: str = Field(..., description="Move in UCI notation, e.g. 'e2e4'")


# ── Responses ──


class PlayerInfo(BaseModel):
    user_id: Optional[uuid.UUID] = None
    username: str
    elo_rating: int
    seat: int
    is_ai: bool = False


class GameResponse(BaseModel):
    game_id: uuid.UUID
    game_type: str
    status: str
    players: list[PlayerInfo]
    created_at: Optional[datetime] = None


class OpenGameResponse(BaseModel):
    games: list[GameResponse]


class GameStateResponse(BaseModel):
    game_id: uuid.UUID
    status: str
    fen: str
    board: list[list[Optional[str]]]
    legal_moves: list[str]
    turn_seat: int
    your_seat: int
    is_check: bool
    game_over: bool
    result: Optional[dict] = None
    last_move: Optional[dict] = None
    move_stack_san: list[str]
    players: list[PlayerInfo]
