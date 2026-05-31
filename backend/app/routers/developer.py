"""
Developer router — analytics and tooling exclusive to the ai_developer role.

Endpoints:
  GET /api/developer/analytics  — per-agent win/loss/draw stats for this developer's agents
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.agent import Agent, IntegrationMode
from app.models.match import Match, MatchParticipant, MatchResult
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/developer", tags=["developer"])

_dev_dep = require_role(UserRole.ai_developer, UserRole.admin)


class AgentAnalytics(BaseModel):
    agent_id: str
    name: str
    game_type: str
    integration_mode: str
    status: str
    elo_rating: int
    total_matches: int
    wins: int
    losses: int
    draws: int
    win_rate: float


@router.get("/analytics", response_model=list[AgentAnalytics])
async def get_developer_analytics(
    user: User = Depends(_dev_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    Per-agent performance breakdown for all agents owned by this developer.
    Only accessible to ai_developer and admin roles.
    """
    agents_result = await db.execute(
        select(Agent).where(Agent.owner_id == user.id).order_by(Agent.created_at.desc())
    )
    agents = agents_result.scalars().all()

    analytics: list[AgentAnalytics] = []

    for agent in agents:
        parts_result = await db.execute(
            select(MatchParticipant).where(MatchParticipant.agent_id == agent.id)
        )
        participations = parts_result.scalars().all()

        total = len(participations)
        wins = draws = losses = 0

        for part in participations:
            match = await db.get(Match, part.match_id)
            if not match or match.result is None:
                continue
            if match.result == MatchResult.draw:
                draws += 1
            elif (
                (match.result == MatchResult.player1_win and part.seat == 1)
                or (match.result == MatchResult.player2_win and part.seat == 2)
            ):
                wins += 1
            else:
                losses += 1

        finished = wins + losses + draws
        win_rate = round((wins / finished) * 100, 1) if finished > 0 else 0.0

        analytics.append(
            AgentAnalytics(
                agent_id=str(agent.id),
                name=agent.name,
                game_type=agent.game_type,
                integration_mode=agent.integration_mode.value,
                status=agent.status.value,
                elo_rating=agent.elo_rating,
                total_matches=total,
                wins=wins,
                losses=losses,
                draws=draws,
                win_rate=win_rate,
            )
        )

    return analytics
