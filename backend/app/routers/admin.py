"""
Admin router — moderation panel endpoints.

Protected by the `admin` role.
Endpoints:
  GET  /api/admin/stats                     — platform overview (users, games, agents)
  GET  /api/admin/users                     — list all users
  POST /api/admin/agents/{id}/pause         — pause an agent
  POST /api/admin/agents/{id}/unpause       — unpause an agent
  POST /api/admin/agents/{id}/ban           — ban an agent
  POST /api/admin/users/{id}/ban            — ban a user account (set role to 'banned')
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.agent import Agent, AgentStatus
from app.models.match import Match
from app.models.user import User, UserRole
from app.services.game import game_manager

router = APIRouter(prefix="/api/admin", tags=["admin"])

_admin_dep = require_role(UserRole.admin)


# ── Schemas ──────────────────────────────────────────────────────────────────


class PlatformStats(BaseModel):
    total_users: int
    total_agents: int
    total_matches: int
    active_games: int
    active_agents: int


class AdminUserEntry(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    role: str
    elo_rating: int
    created_at: datetime


class AdminAgentEntry(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    game_type: str
    status: str
    elo_rating: int
    webhook_url: Optional[str]
    continuous_queue: bool
    created_at: datetime


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/stats", response_model=PlatformStats)
async def get_stats(
    _: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
):
    """High-level platform statistics."""
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    total_agents = (await db.execute(select(func.count()).select_from(Agent))).scalar() or 0
    total_matches = (await db.execute(select(func.count()).select_from(Match))).scalar() or 0
    active_agents = (
        await db.execute(
            select(func.count()).select_from(Agent).where(Agent.status == AgentStatus.active)
        )
    ).scalar() or 0

    active_games = len([s for s in game_manager.sessions.values() if s.status == "active"])

    return PlatformStats(
        total_users=total_users,
        total_agents=total_agents,
        total_matches=total_matches,
        active_games=active_games,
        active_agents=active_agents,
    )


@router.get("/users")
async def list_users(
    _: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
):
    """List all registered users."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        AdminUserEntry(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role.value,
            elo_rating=u.elo_rating,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/agents")
async def list_all_agents(
    _: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
):
    """List all registered agents across all owners."""
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    agents = result.scalars().all()
    return [
        AdminAgentEntry(
            id=a.id,
            name=a.name,
            owner_id=a.owner_id,
            game_type=a.game_type,
            status=a.status.value,
            elo_rating=a.elo_rating,
            webhook_url=a.webhook_url,
            continuous_queue=a.continuous_queue,
            created_at=a.created_at,
        )
        for a in agents
    ]


async def _get_agent_or_404(agent_id: uuid.UUID, db: AsyncSession) -> Agent:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent


@router.post("/agents/{agent_id}/pause", status_code=200)
async def pause_agent(
    agent_id: uuid.UUID,
    _: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
):
    """Pause an active agent — stops it from being queued or making webhook calls."""
    agent = await _get_agent_or_404(agent_id, db)
    if agent.status == AgentStatus.banned:
        raise HTTPException(status_code=400, detail="Cannot pause a banned agent.")
    agent.status = AgentStatus.paused
    await db.commit()
    return {"detail": "Agent paused", "agent_id": str(agent_id)}


@router.post("/agents/{agent_id}/unpause", status_code=200)
async def unpause_agent(
    agent_id: uuid.UUID,
    _: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
):
    """Re-activate a paused agent."""
    agent = await _get_agent_or_404(agent_id, db)
    if agent.status == AgentStatus.banned:
        raise HTTPException(status_code=400, detail="Cannot unpause a banned agent.")
    agent.status = AgentStatus.active
    await db.commit()
    return {"detail": "Agent unpaused", "agent_id": str(agent_id)}


@router.post("/agents/{agent_id}/ban", status_code=200)
async def ban_agent(
    agent_id: uuid.UUID,
    _: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
):
    """Permanently ban an agent — removes it from all queues."""
    agent = await _get_agent_or_404(agent_id, db)
    agent.status = AgentStatus.banned
    await db.commit()
    return {"detail": "Agent banned", "agent_id": str(agent_id)}


@router.get("/active-games")
async def get_active_games(_: User = Depends(_admin_dep)):
    """List all currently active in-memory game sessions."""
    sessions = [s for s in game_manager.sessions.values() if s.status == "active"]
    return [
        {
            "game_id": str(s.match_id),
            "game_type": s.game_type,
            "players": [p.username for p in s.players.values()],
            "started_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]
