"""
Game manager — in-memory active game session tracking.
Handles creation, joining, move execution, and AI bot responses.
Supports both 2-player (chess) and 3-7-player (poker) games.
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
    webhook_url: Optional[str] = None   # set for registered webhook agents
    script_path: Optional[str] = None   # set for uploaded script agents
    agent_id: Optional[uuid.UUID] = None  # DB agent id for registered agents

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
BOT_POKERBOT = "pokerbot"

BOT_INFO = {
    BOT_RANDOM: {"name": "Random Bot 🎲", "elo": 400},
    BOT_CHESSBOT: {"name": "ChessBot AI 🧠", "elo": 1500},
    BOT_POKERBOT: {"name": "PokerBot AI 🤖", "elo": 1200},
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
    max_seats: int = 2        # how many seats the creator configured
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_full(self) -> bool:
        return len(self.players) >= self.max_seats

    def next_free_seat(self) -> Optional[int]:
        """Return the next available seat number (1-indexed), or None."""
        for s in range(1, self.max_seats + 1):
            if s not in self.players:
                return s
        return None


class GameManager:
    """Singleton that manages all active game sessions in memory."""

    def __init__(self):
        self.sessions: dict[uuid.UUID, GameSession] = {}

    # ── Creation ──

    async def create_game(
        self,
        db: AsyncSession,
        game_type: str,
        creator_id: Optional[uuid.UUID],
        creator_username: str,
        creator_elo: int,
        vs_ai: bool = False,
        bot_type: str = BOT_RANDOM,
        max_players: int = 2,
        creator_is_agent: bool = False,
        creator_webhook_url: Optional[str] = None,
        creator_script_path: Optional[str] = None,
        creator_agent_id: Optional[uuid.UUID] = None,
    ) -> GameSession:
        engine = get_engine(game_type)

        # For poker, enforce 3-7 players; for chess, always 2
        if game_type == "poker":
            max_seats = max(3, min(7, max_players))
        else:
            max_seats = 2

        # Create initial state — poker engine accepts num_players kwarg
        if game_type == "poker":
            state = engine.create_initial_state(num_players=max_seats)
        else:
            state = engine.create_initial_state()

        match_id = uuid.uuid4()

        creator = PlayerSlot(
            user_id=creator_id,
            username=creator_username,
            elo_rating=creator_elo,
            seat=1,
            is_ai=creator_is_agent,
            webhook_url=creator_webhook_url,
            script_path=creator_script_path,
            agent_id=creator_agent_id,
        )

        session = GameSession(
            match_id=match_id,
            game_type=game_type,
            engine=engine,
            state=state,
            players={1: creator},
            max_seats=max_seats,
        )

        if vs_ai:
            # Fill all remaining seats with AI bots
            info = BOT_INFO.get(bot_type, BOT_INFO[BOT_RANDOM])
            for seat in range(2, max_seats + 1):
                ai = PlayerSlot(
                    user_id=None,
                    username=f"{info['name']} #{seat - 1}",
                    elo_rating=info["elo"],
                    seat=seat,
                    is_ai=True,
                )
                session.players[seat] = ai
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
            agent_id=creator_agent_id,
            seat=1,
            elo_before=creator_elo,
        ))

        if vs_ai:
            for seat in range(2, max_seats + 1):
                db.add(MatchParticipant(
                    match_id=match_id,
                    seat=seat,
                    elo_before=800,
                ))

        await db.flush()
        return session

    # ── Joining ──

    async def join_game(
        self,
        db: AsyncSession,
        match_id: uuid.UUID,
        player_id: Optional[uuid.UUID],
        player_username: str,
        player_elo: int,
        is_agent: bool = False,
        webhook_url: Optional[str] = None,
        script_path: Optional[str] = None,
        agent_id: Optional[uuid.UUID] = None,
    ) -> GameSession:
        session = self.sessions.get(match_id)
        if not session:
            raise ValueError("Game not found")
        if session.status != "waiting":
            raise ValueError("Game is not open for joining")
        if any(p.user_id == player_id for p in session.players.values() if p.user_id):
            raise ValueError("You are already in this game")

        seat = session.next_free_seat()
        if seat is None:
            raise ValueError("Game is full")

        joiner = PlayerSlot(
            user_id=player_id,
            username=player_username,
            elo_rating=player_elo,
            seat=seat,
            is_ai=is_agent,
            webhook_url=webhook_url,
            script_path=script_path,
            agent_id=agent_id,
        )
        session.players[seat] = joiner

        # If all seats are filled, start the game
        if session.is_full:
            session.status = "active"

        db.add(MatchParticipant(
            match_id=match_id,
            player_id=player_id,
            agent_id=agent_id,
            seat=seat,
            elo_before=player_elo,
        ))
        await db.flush()
        return session

    async def join_ai(
        self,
        db: AsyncSession,
        match_id: uuid.UUID,
        bot_type: str = BOT_RANDOM,
    ) -> GameSession:
        """Add an AI player to an open game."""
        session = self.sessions.get(match_id)
        if not session:
            raise ValueError("Game not found")
        if session.status != "waiting":
            raise ValueError("Game is not open for joining")

        seat = session.next_free_seat()
        if seat is None:
            raise ValueError("Game is full")

        info = BOT_INFO.get(bot_type, BOT_INFO[BOT_RANDOM])
        ai_count = sum(1 for p in session.players.values() if p.is_ai)

        ai = PlayerSlot(
            user_id=None,
            username=f"{info['name']} #{ai_count + 1}",
            elo_rating=info["elo"],
            seat=seat,
            is_ai=True,
        )
        session.players[seat] = ai
        session.bot_type = session.bot_type or bot_type  # keep first bot_type

        # If all seats are filled, start the game
        if session.is_full:
            session.status = "active"

        db.add(MatchParticipant(
            match_id=match_id,
            seat=seat,
            elo_before=info["elo"],
        ))
        await db.flush()
        return session

    # ── Moves ──

    async def make_move(
        self,
        db: AsyncSession,
        match_id: uuid.UUID,
        seat: int,
        move_str: str,
    ) -> tuple[GameSession, dict]:
        session = self.sessions.get(match_id)
        if not session:
            raise ValueError("Game not found")
        if session.status != "active":
            raise ValueError("Game is not active")

        current_turn = session.engine.get_current_turn(session.state)
        if current_turn != seat:
            raise ValueError("Not your turn")

        if not session.engine.validate_move(session.state, move_str):
            raise ValueError("Invalid move")

        # Apply move
        new_state = session.engine.apply_move(session.state, move_str)
        san = session.engine.get_last_move_san(new_state)
        session.state = new_state

        # Build move_info (generic — works for both chess and poker)
        turn_num = getattr(new_state, '_turn_number', 0)
        if not turn_num and hasattr(new_state, '_move_stack_san'):
            turn_num = len(new_state._move_stack_san)

        move_info = {
            "turn": turn_num,
            "seat": seat,
            "move": move_str,
            "san": san or move_str,
        }

        # Persist move
        db.add(MatchMove(
            match_id=match_id,
            turn_number=move_info["turn"],
            seat=seat,
            move_payload={"move": move_str, "san": san},
        ))

        # Check terminal
        terminal = session.engine.is_terminal(session.state)
        if terminal:
            session.status = "finished"
            session.result = terminal
            await self._finalize_match(db, session, terminal)

        await db.flush()
        return session, move_info

    async def check_and_finalize(
        self,
        db: AsyncSession,
        match_id: uuid.UUID,
    ) -> bool:
        """Check if the game is terminal and finalize if so.
        Call this after start_next_hand to detect poker game-over.
        Returns True if the game ended."""
        session = self.sessions.get(match_id)
        if not session or session.status != "active":
            return False

        terminal = session.engine.is_terminal(session.state)
        if terminal:
            session.status = "finished"
            session.result = terminal
            await self._finalize_match(db, session, terminal)
            await db.flush()
            return True
        return False

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

        # Visible pause so players can follow the action
        await asyncio.sleep(1.25)

        move: Optional[str] = None

        # ── Webhook agent (registered external bot) ──────────────────────────
        if ai_player.webhook_url:
            from app.services.webhook import call_agent_webhook, build_webhook_payload
            payload = build_webhook_payload(session, current_turn)
            move = await call_agent_webhook(ai_player.webhook_url, payload)
            if not move:
                move = pick_random_move(session.engine, session.state)

        # ── Uploaded script agent ──────────────────────────────────────────────
        elif getattr(ai_player, 'script_path', None):
            import subprocess
            import json
            from app.services.webhook import build_webhook_payload
            payload = build_webhook_payload(session, current_turn)
            try:
                proc = subprocess.run(
                    ["python", ai_player.script_path],
                    input=json.dumps(payload).encode('utf-8'),
                    capture_output=True,
                    timeout=5.0
                )
                if proc.returncode == 0:
                    result = json.loads(proc.stdout)
                    move = result.get("move")
            except Exception:
                pass
            if not move:
                move = pick_random_move(session.engine, session.state)

        # ── Built-in bots ─────────────────────────────────────────────────────
        elif session.bot_type == BOT_CHESSBOT:
            from app.games.bots.hf_chessbot import pick_hf_move
            move = pick_hf_move(session.engine, session.state, temperature=0.3)
        elif session.bot_type == BOT_POKERBOT:
            from app.games.bots.hf_pokerbot import pick_hf_poker_move
            move = pick_hf_poker_move(session.engine, session.state)
        else:
            move = pick_random_move(session.engine, session.state)

        # Fallback to random if move is completely invalid so the loop never stalls
        try:
            return await self.make_move(db, match_id, current_turn, move)
        except ValueError:
            fallback = pick_random_move(session.engine, session.state)
            return await self.make_move(db, match_id, current_turn, fallback)

    # ── Resign / Fold-out ──

    async def resign(
        self, db: AsyncSession, match_id: uuid.UUID, seat: int
    ) -> GameSession:
        session = self.sessions.get(match_id)
        if not session or session.status != "active":
            raise ValueError("Game not active")

        # For 2-player: the other player wins
        # For multiplayer: just mark as finished (simplification)
        other_seats = [s for s in session.players if s != seat]
        if len(other_seats) == 1:
            winner = other_seats[0]
        else:
            winner = other_seats[0]  # first remaining player

        result_key = f"player{winner}_win"
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

    @staticmethod
    def _elo_expected(rating_a: int, rating_b: int) -> float:
        """Expected score of player A vs player B."""
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    @staticmethod
    def _elo_delta(rating: int, opponent_rating: int, score: float, k: int = 32) -> int:
        """Calculate ELO change for a single pairing."""
        expected = GameManager._elo_expected(rating, opponent_rating)
        return round(k * (score - expected))

    async def _finalize_match(
        self, db: AsyncSession, session: GameSession, terminal: dict
    ) -> None:
        from app.models.user import User

        result_str = terminal["result"]
        # Map result to enum — for multi-player poker, any "playerN_win"
        # is stored as player1_win (the actual winner is tracked in elo_after)
        if result_str == "draw":
            result_enum = MatchResult.draw
        elif result_str == "player2_win":
            result_enum = MatchResult.player2_win
        elif "win" in result_str:
            result_enum = MatchResult.player1_win
        else:
            result_enum = None

        # Update Match record
        match = await db.get(Match, session.match_id)
        if match:
            match.result = result_enum
            match.final_state = session.state.to_dict()
            match.ended_at = datetime.now(timezone.utc)

        # ── ELO Updates ──
        # Determine the winning seat(s)
        winner_seat = terminal.get("winner_seat")

        # Collect all participants with their current ELO
        participants = []  # list of (seat, player_slot, MatchParticipant or None)
        from sqlalchemy import select
        result_rows = await db.execute(
            select(MatchParticipant).where(MatchParticipant.match_id == session.match_id)
        )
        mp_map = {mp.seat: mp for mp in result_rows.scalars().all()}

        for seat, slot in session.players.items():
            mp = mp_map.get(seat)
            participants.append((seat, slot, mp))

        if len(participants) == 2:
            # ── 2-player ELO (chess) ──
            (s1, p1, mp1), (s2, p2, mp2) = participants
            if result_str == "draw":
                score1, score2 = 0.5, 0.5
            elif winner_seat == s1:
                score1, score2 = 1.0, 0.0
            else:
                score1, score2 = 0.0, 1.0

            delta1 = self._elo_delta(p1.elo_rating, p2.elo_rating, score1)
            delta2 = self._elo_delta(p2.elo_rating, p1.elo_rating, score2)

            for slot, mp, delta in [(p1, mp1, delta1), (p2, mp2, delta2)]:
                new_elo = max(100, slot.elo_rating + delta)
                if mp:
                    mp.elo_after = new_elo
                if slot.user_id:
                    user = await db.get(User, slot.user_id)
                    if user:
                        user.elo_rating = new_elo
                        slot.elo_rating = new_elo
                elif getattr(slot, "agent_id", None):
                    from app.models.agent import Agent
                    agent = await db.get(Agent, slot.agent_id)
                    if agent:
                        agent.elo_rating = new_elo
                        slot.elo_rating = new_elo
        else:
            # ── Multi-player ELO (poker) ──
            # Winner gains from each opponent; losers lose to the winner
            for seat, slot, mp in participants:
                if seat == winner_seat:
                    # Winner: sum of expected-vs-actual against each opponent
                    total_delta = 0
                    for s2, p2, _ in participants:
                        if s2 != seat:
                            total_delta += self._elo_delta(
                                slot.elo_rating, p2.elo_rating, 1.0, k=32
                            )
                    new_elo = max(100, slot.elo_rating + total_delta)
                else:
                    # Loser: lost to the winner
                    winner_slot = session.players.get(winner_seat)
                    if winner_slot:
                        delta = self._elo_delta(
                            slot.elo_rating, winner_slot.elo_rating, 0.0, k=32
                        )
                    else:
                        delta = -16
                    new_elo = max(100, slot.elo_rating + delta)

                if mp:
                    mp.elo_after = new_elo
                if slot.user_id:
                    user = await db.get(User, slot.user_id)
                    if user:
                        user.elo_rating = new_elo
                        slot.elo_rating = new_elo
                elif getattr(slot, "agent_id", None):
                    from app.models.agent import Agent
                    agent = await db.get(Agent, slot.agent_id)
                    if agent:
                        agent.elo_rating = new_elo
                        slot.elo_rating = new_elo

        # ── Auto re-queue continuous agents ──
        from app.models.agent import AgentStatus
        from app.routers.matchmaking import _get_queue, _QueueEntry, _try_match
        
        re_queued_game_types = set()
        for seat, slot in session.players.items():
            if slot.is_ai and getattr(slot, "agent_id", None):
                agent = await db.get(Agent, slot.agent_id)
                if agent and agent.continuous_queue and agent.status == AgentStatus.active:
                    q = _get_queue(agent.game_type)
                    if not any(e.entity_id == agent.id for e in q):
                        entry = _QueueEntry(
                            entity_id=agent.id,
                            username=agent.name,
                            elo=agent.elo_rating,
                            game_type=agent.game_type,
                            is_agent=True,
                            webhook_url=agent.webhook_url,
                            script_path=agent.script_path,
                            continuous=True,
                        )
                        q.append(entry)
                        re_queued_game_types.add(agent.game_type)
        
        # Trigger matchmaking for any queues that got new agents
        for game_type in re_queued_game_types:
            import asyncio
            async def run_matchmaking(t_game_type):
                from app.database import async_session
                try:
                    async with async_session() as bg_db:
                        await _try_match(t_game_type, bg_db)
                except Exception as e:
                    pass
            asyncio.create_task(run_matchmaking(game_type))

# Module-level singleton
game_manager = GameManager()

