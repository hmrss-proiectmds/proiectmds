"""
Matchmaking router — Redis-backed queue for pairing players and agents.

Endpoints:
  POST /api/matchmaking/queue       — join the matchmaking pool
  DELETE /api/matchmaking/queue     — leave the matchmaking pool
  GET  /api/matchmaking/queue       — inspect current queue (admin-friendly)
  POST /api/matchmaking/queue/agent — enqueue a registered webhook agent
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.agent import Agent, AgentStatus
from app.models.user import User, UserRole
from app.services.game import game_manager

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/matchmaking", tags=["matchmaking"])


# ── In-memory queue (one per game type) ──────────────────────────────────────
# A production system would back this with Redis sorted sets; for now a simple
# dict of lists is sufficient and avoids an extra dependency.

class _QueueEntry:
    def __init__(
        self,
        entity_id: uuid.UUID,
        username: str,
        elo: int,
        game_type: str,
        is_agent: bool = False,
        webhook_url: Optional[str] = None,
        script_path: Optional[str] = None,
        continuous: bool = False,
    ):
        self.entity_id = entity_id
        self.username = username
        self.elo = elo
        self.game_type = game_type
        self.is_agent = is_agent
        self.webhook_url = webhook_url
        self.script_path = script_path
        self.continuous = continuous
        self.joined_at = datetime.now(timezone.utc)


# game_type → list[_QueueEntry]
_queues: dict[str, list[_QueueEntry]] = {}


def _get_queue(game_type: str) -> list[_QueueEntry]:
    return _queues.setdefault(game_type, [])


def _remove_from_queue(entity_id: uuid.UUID, game_type: str) -> bool:
    q = _get_queue(game_type)
    before = len(q)
    _queues[game_type] = [e for e in q if e.entity_id != entity_id]
    return len(_queues[game_type]) < before


async def _try_match(game_type: str, db: AsyncSession):
    """If two or more entries are queued, pair the first two and start a game."""
    q = _get_queue(game_type)
    if len(q) < 2:
        return

    e1, e2 = q[0], q[1]
    _queues[game_type] = q[2:]

    log.info("Matched %s vs %s in %s", e1.username, e2.username, game_type)

    # Create game via game_manager (creator = e1)
    session = await game_manager.create_game(
        db=db,
        game_type=game_type,
        creator_id=e1.entity_id if not e1.is_agent else None,
        creator_username=e1.username,
        creator_elo=e1.elo,
        vs_ai=False,
        creator_is_agent=e1.is_agent,
        creator_webhook_url=e1.webhook_url,
        creator_script_path=e1.script_path,
        creator_agent_id=e1.entity_id if e1.is_agent else None,
    )

    # Join e2
    await game_manager.join_game(
        db=db,
        match_id=session.match_id,
        player_id=e2.entity_id if not e2.is_agent else None,
        player_username=e2.username,
        player_elo=e2.elo,
        is_agent=e2.is_agent,
        webhook_url=e2.webhook_url,
        script_path=e2.script_path,
        agent_id=e2.entity_id if e2.is_agent else None,
    )
    await db.commit()
    log.info("Game %s created for matched pair", session.match_id)

    # Kickstart AI if first turn belongs to an AI (e.g. AI vs AI match)
    import asyncio
    current_turn = session.engine.get_current_turn(session.state)
    first_player = session.players.get(current_turn)
    if first_player and first_player.is_ai:
        from app.routers.games import _run_ai_loop
        asyncio.create_task(_run_ai_loop(session.match_id))


# ── Schemas ──────────────────────────────────────────────────────────────────

class JoinQueueRequest(BaseModel):
    game_type: str = "chess"


class AgentQueueRequest(BaseModel):
    agent_id: uuid.UUID
    game_type: str = "chess"


class QueueEntry(BaseModel):
    entity_id: uuid.UUID
    username: str
    elo: int
    game_type: str
    is_agent: bool
    continuous: bool
    joined_at: datetime


class QueueStatusResponse(BaseModel):
    queues: dict[str, list[QueueEntry]]


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/queue", status_code=status.HTTP_202_ACCEPTED)
async def join_queue(
    body: JoinQueueRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join the matchmaking pool as a human player."""
    game_type = body.game_type.lower()
    q = _get_queue(game_type)

    # Prevent duplicate entries
    if any(e.entity_id == current_user.id for e in q):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already in the queue for this game type.",
        )

    entry = _QueueEntry(
        entity_id=current_user.id,
        username=current_user.username,
        elo=current_user.elo_rating,
        game_type=game_type,
    )
    q.append(entry)
    log.info("%s joined %s queue (queue size=%d)", current_user.username, game_type, len(q))

    await _try_match(game_type, db)

    return {
        "detail": "Joined queue",
        "game_type": game_type,
        "queue_position": next(
            (i + 1 for i, e in enumerate(_get_queue(game_type)) if e.entity_id == current_user.id),
            None,
        ),
    }


@router.delete("/queue", status_code=status.HTTP_200_OK)
async def leave_queue(
    game_type: str = "chess",
    current_user: User = Depends(get_current_user),
):
    """Leave the matchmaking queue."""
    removed = _remove_from_queue(current_user.id, game_type.lower())
    if not removed:
        raise HTTPException(status_code=404, detail="You are not in the queue.")
    return {"detail": "Left queue"}


@router.post("/queue/agent", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_agent(
    body: AgentQueueRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue a registered webhook agent owned by the current user."""
    agent = await db.get(Agent, body.agent_id)
    if not agent or agent.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Agent not found.")
    if agent.status != AgentStatus.active:
        raise HTTPException(status_code=400, detail="Agent is not active.")
    if not agent.webhook_url and not agent.script_path:
        raise HTTPException(status_code=400, detail="Agent has no webhook URL or script registered.")

    game_type = body.game_type.lower()
    q = _get_queue(game_type)

    if any(e.entity_id == agent.id for e in q):
        _remove_from_queue(agent.id, game_type)
        return {"detail": "Agent removed from queue", "status": "removed"}

    entry = _QueueEntry(
        entity_id=agent.id,
        username=agent.name,
        elo=agent.elo_rating,
        game_type=game_type,
        is_agent=True,
        webhook_url=agent.webhook_url,
        script_path=agent.script_path,
        continuous=agent.continuous_queue,
    )
    q.append(entry)
    log.info("Agent %s joined %s queue", agent.name, game_type)

    await _try_match(game_type, db)

    return {"detail": "Agent queued", "agent_id": str(agent.id), "game_type": game_type}


@router.get("/queue", response_model=QueueStatusResponse)
async def get_queue_status(
    _: User = Depends(require_role(UserRole.admin, UserRole.ai_developer, UserRole.ai_agent_owner)),
):
    """Inspect the current matchmaking queues (admin/developer view)."""
    return QueueStatusResponse(
        queues={
            gt: [
                QueueEntry(
                    entity_id=e.entity_id,
                    username=e.username,
                    elo=e.elo,
                    game_type=e.game_type,
                    is_agent=e.is_agent,
                    continuous=e.continuous,
                    joined_at=e.joined_at,
                )
                for e in entries
            ]
            for gt, entries in _queues.items()
        }
    )
