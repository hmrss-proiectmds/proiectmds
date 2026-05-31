"""
Agent Owner router — fleet management exclusive to the ai_agent_owner role.

Endpoints:
  GET /api/owner/fleet  — all webhook agents with live status (queue, in-game)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.agent import Agent, IntegrationMode
from app.models.match import MatchParticipant
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/owner", tags=["owner"])

_owner_dep = require_role(UserRole.ai_agent_owner, UserRole.admin)


class AgentFleetEntry(BaseModel):
    agent_id: str
    name: str
    game_type: str
    webhook_url: Optional[str]
    status: str
    elo_rating: int
    continuous_queue: bool
    in_queue: bool
    in_game_id: Optional[str]
    match_count: int
    created_at: str


@router.get("/fleet", response_model=list[AgentFleetEntry])
async def get_agent_fleet(
    user: User = Depends(_owner_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    Fleet overview of all webhook agents owned by this agent owner, with live status.
    Only accessible to ai_agent_owner and admin roles.
    """
    agents_result = await db.execute(
        select(Agent)
        .where(
            Agent.owner_id == user.id,
            Agent.integration_mode == IntegrationMode.webhook,
        )
        .order_by(Agent.created_at.desc())
    )
    agents = agents_result.scalars().all()

    from app.services.game import game_manager
    from app.routers.matchmaking import _queues

    fleet: list[AgentFleetEntry] = []

    for agent in agents:
        count_result = await db.execute(
            select(MatchParticipant).where(MatchParticipant.agent_id == agent.id)
        )
        match_count = len(count_result.scalars().all())

        q = _queues.get(agent.game_type, [])
        in_queue = any(e.entity_id == agent.id for e in q)

        in_game_id: Optional[str] = None
        for session in game_manager.sessions.values():
            if session.status == "active":
                for slot in session.players.values():
                    if slot.is_ai and slot.agent_id == agent.id:
                        in_game_id = str(session.match_id)
                        break
            if in_game_id:
                break

        fleet.append(
            AgentFleetEntry(
                agent_id=str(agent.id),
                name=agent.name,
                game_type=agent.game_type,
                webhook_url=agent.webhook_url,
                status=agent.status.value,
                elo_rating=agent.elo_rating,
                continuous_queue=agent.continuous_queue,
                in_queue=in_queue,
                in_game_id=in_game_id,
                match_count=match_count,
                created_at=agent.created_at.isoformat(),
            )
        )

    return fleet
