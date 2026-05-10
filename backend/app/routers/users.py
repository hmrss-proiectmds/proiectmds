"""
Users router: profile and leaderboard endpoints.

The leaderboard is cross-entity — humans and AI agents compete on one scale.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.agent import Agent, AgentStatus
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    elo_rating: int
    entity_type: str  # "human" | "agent"
    role: str         # human role or "agent"
    game_type: str | None = None   # set for agents


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    include_agents: bool = Query(True, description="Include registered AI agents"),
    db: AsyncSession = Depends(get_db),
):
    """Return the top 50 entities (humans + agents) by ELO rating."""
    combined: list[dict] = []

    # Fetch all users
    users_result = await db.execute(select(User))
    for u in users_result.scalars().all():
        combined.append({
            "username": u.username,
            "elo_rating": u.elo_rating,
            "entity_type": "human",
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "game_type": None,
        })

    # Optionally fetch active agents
    if include_agents:
        agents_result = await db.execute(
            select(Agent).where(Agent.status == AgentStatus.active)
        )
        for a in agents_result.scalars().all():
            combined.append({
                "username": a.name,
                "elo_rating": a.elo_rating,
                "entity_type": "agent",
                "role": "agent",
                "game_type": a.game_type,
            })

    # Sort by ELO descending, limit 50
    combined.sort(key=lambda x: x["elo_rating"], reverse=True)
    combined = combined[:50]

    entries = [
        LeaderboardEntry(rank=i + 1, **entry)
        for i, entry in enumerate(combined)
    ]
    return LeaderboardResponse(entries=entries)
