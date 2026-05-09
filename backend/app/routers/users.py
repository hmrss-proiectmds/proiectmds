"""
Users router: profile and leaderboard endpoints.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
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
    role: str


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    """Return top 50 users by ELO rating."""
    result = await db.execute(
        select(User).order_by(User.elo_rating.desc()).limit(50)
    )
    users = result.scalars().all()

    entries = []
    for i, u in enumerate(users, start=1):
        entries.append(LeaderboardEntry(
            rank=i,
            username=u.username,
            elo_rating=u.elo_rating,
            role=u.role.value if hasattr(u.role, 'value') else str(u.role),
        ))

    return LeaderboardResponse(entries=entries)

