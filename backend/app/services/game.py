"""
Game manager — in-memory active game session tracking.
Handles creation, joining, move execution, and AI bot responses.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.games.base import GameEngine, GameState
from app.games.bots.random_bot import pick_random_move
from app.games.registry import get_engine
from app.models.match import Match, MatchMode, MatchMove, MatchParticipant, MatchResult


@dataclass
class PlayerSlot:
    user_id: Optional[uuid.UUID]
    username: str
    elo_rating: int
    seat: int
    is_ai: bool = False

    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id) if self.user_id else None,
            "username": self.username,
            "elo_rating": self.elo_rating,
            "seat": self.seat,
            "is_ai": self.is_ai,
        }


# Bot type constants
BOT_RANDOM = "random"
BOT_CHESSBOT = "chessbot"

BOT_INFO = {
    BOT_RANDOM: {"name": "Random Bot 🎲", "elo": 400},
    BOT_CHESSBOT: {"name": "ChessBot AI 🧠", "elo": 1500},
}


@dataclass
class GameSession:
    match_id: uuid.UUID
    game_type: str
    engine: GameEngine
    state: GameState
    players: dict[int, PlayerSlot] = field(default_factory=dict)
    status: str = "waiting"  # waiting | active | finished
    result: Optional[dict] = None
    bot_type: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GameManager:
    """Singleton that manages all active game sessions in memory."""

    def __init__(self):
        self.sessions: dict[uuid.UUID, GameSession] = {}

    # ── Creation ──

    async def create_game(
        self,
        db: AsyncSession,
        game_type: str,
        creator_id: uuid.UUID,
        creator_username: str,
        creator_elo: int,
        vs_ai: bool = False,
        bot_type: str = BOT_RANDOM,
    ) -> GameSession:
        engine = get_engine(game_type)
        state = engine.create_initial_state()
        match_id = uuid.uuid4()

        creator = PlayerSlot(
            user_id=creator_id,
            username=creator_username,
            elo_rating=creator_elo,
            seat=1,
        )

        session = GameSession(
            match_id=match_id,
            game_type=game_type,
            engine=engine,
            state=state,
            players={1: creator},
        )

        if vs_ai:
            info = BOT_INFO.get(bot_type, BOT_INFO[BOT_RANDOM])
            ai = PlayerSlot(
                user_id=None,
                username=info["name"],
                elo_rating=info["elo"],
                seat=2,
                is_ai=True,
            )
            session.players[2] = ai
            session.bot_type = bot_type
            session.status = "active"

        self.sessions[match_id] = session

        # Persist to DB
        match = Match(
            id=match_id,
            game_type=game_type,
            mode=MatchMode.live,
        )
        db.add(match)

        db.add(MatchParticipant(
            match_id=match_id,
            player_id=creator_id,
            seat=1,
            elo_before=creator_elo,
        ))

        if vs_ai:
            db.add(MatchParticipant(
                match_id=match_id,
                seat=2,
                elo_before=800,
            ))

        await db.flush()
        return session

    # ── Joining ──

    async def join_game(
        self,
        db: AsyncSession,
        match_id: uuid.UUID,
        player_id: uuid.UUID,
        player_username: str,
        player_elo: int,
    ) -> GameSession:
        session = self.sessions.get(match_id)
        if not session:
            raise ValueError("Game not found")
        if session.status != "waiting":
            raise ValueError("Game is not open for joining")
        if any(p.user_id == player_id for p in session.players.values()):
            raise ValueError("You are already in this game")

        joiner = PlayerSlot(
            user_id=player_id,
            username=player_username,
            elo_rating=player_elo,
            seat=2,
        )
        session.players[2] = joiner
        session.status = "active"

        db.add(MatchParticipant(
            match_id=match_id,
            player_id=player_id,
            seat=2,
            elo_before=player_elo,
        ))
        await db.flush()
        return session

    # ── Moves ──

    async def make_move(
        self,
        db: AsyncSession,
        match_id: uuid.UUID,
        seat: int,
        move_uci: str,
    ) -> tuple[GameSession, dict]:
        session = self.sessions.get(match_id)
        if not session:
            raise ValueError("Game not found")
        if session.status != "active":
            raise ValueError("Game is not active")

        current_turn = session.engine.get_current_turn(session.state)
        if current_turn != seat:
            raise ValueError("Not your turn")

        if not session.engine.validate_move(session.state, move_uci):
            raise ValueError("Invalid move")

        # Apply move
        new_state = session.engine.apply_move(session.state, move_uci)
        san = session.engine.get_last_move_san(new_state)
        session.state = new_state

        move_info = {
            "turn": len(new_state._move_stack_san),
            "seat": seat,
            "uci": move_uci,
            "san": san or move_uci,
        }

        # Persist move
        db.add(MatchMove(
            match_id=match_id,
            turn_number=move_info["turn"],
            seat=seat,
            move_payload={"uci": move_uci, "san": san},
        ))

        # Check terminal
        terminal = session.engine.is_terminal(session.state)
        if terminal:
            session.status = "finished"
            session.result = terminal
            await self._finalize_match(db, session, terminal)

        await db.flush()
        return session, move_info

    async def make_ai_move(
        self,
        db: AsyncSession,
        match_id: uuid.UUID,
    ) -> tuple[GameSession, dict] | None:
        """Let the AI make its move. Returns None if it's not the AI's turn."""
        session = self.sessions.get(match_id)
        if not session or session.status != "active":
            return None

        current_turn = session.engine.get_current_turn(session.state)
        ai_player = session.players.get(current_turn)
        if not ai_player or not ai_player.is_ai:
            return None

        # Small delay to feel natural
        await asyncio.sleep(0.5)

        if session.bot_type == BOT_CHESSBOT:
            from app.games.bots.hf_chessbot import pick_hf_move
            move_uci = pick_hf_move(session.engine, session.state, temperature=0.3)
        else:
            move_uci = pick_random_move(session.engine, session.state)

        return await self.make_move(db, match_id, current_turn, move_uci)

    # ── Resign ──

    async def resign(
        self, db: AsyncSession, match_id: uuid.UUID, seat: int
    ) -> GameSession:
        session = self.sessions.get(match_id)
        if not session or session.status != "active":
            raise ValueError("Game not active")

        winner = 2 if seat == 1 else 1
        result_key = "player1_win" if winner == 1 else "player2_win"
        terminal = {"result": result_key, "reason": "resignation"}
        session.status = "finished"
        session.result = terminal
        await self._finalize_match(db, session, terminal)
        await db.flush()
        return session

    # ── Queries ──

    def get_session(self, match_id: uuid.UUID) -> GameSession | None:
        return self.sessions.get(match_id)

    def get_open_games(self) -> list[GameSession]:
        return [s for s in self.sessions.values() if s.status == "waiting"]

    def get_player_seat(self, match_id: uuid.UUID, user_id: uuid.UUID) -> int | None:
        session = self.sessions.get(match_id)
        if not session:
            return None
        for seat, p in session.players.items():
            if p.user_id == user_id:
                return seat
        return None

    # ── Internal ──

    async def _finalize_match(
        self, db: AsyncSession, session: GameSession, terminal: dict
    ) -> None:
        result_str = terminal["result"]
        result_enum = {
            "player1_win": MatchResult.player1_win,
            "player2_win": MatchResult.player2_win,
            "draw": MatchResult.draw,
        }.get(result_str)

        match = await db.get(Match, session.match_id)
        if match:
            match.result = result_enum
            match.final_state = session.state.to_dict()
            match.ended_at = datetime.now(timezone.utc)


# Module-level singleton
game_manager = GameManager()
