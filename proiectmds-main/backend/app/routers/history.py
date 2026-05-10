"""
Match history router — returns paginated history for the current user.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.match import Match, MatchParticipant
from app.models.user import User

router = APIRouter(prefix="/api/history", tags=["history"])


class MatchHistoryEntry(BaseModel):
    match_id: UUID
    game_type: str
    result: Optional[str] = None
    your_seat: int
    elo_before: int
    elo_after: Optional[int] = None
    elo_change: Optional[int] = None
    opponents: list[str]
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    outcome: str  # "win", "loss", "draw"


class MatchHistoryResponse(BaseModel):
    matches: list[MatchHistoryEntry]
    total: int


@router.get("", response_model=MatchHistoryResponse)
async def get_match_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated match history for the current user."""
    user_id = current_user.id

    # Count total matches
    count_q = (
        select(func.count())
        .select_from(MatchParticipant)
        .join(Match, MatchParticipant.match_id == Match.id)
        .where(MatchParticipant.player_id == user_id)
        .where(Match.ended_at.isnot(None))
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Fetch matches
    offset = (page - 1) * per_page
    matches_q = (
        select(Match)
        .join(MatchParticipant, Match.id == MatchParticipant.match_id)
        .where(MatchParticipant.player_id == user_id)
        .where(Match.ended_at.isnot(None))
        .options(selectinload(Match.participants))
        .order_by(Match.ended_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(matches_q)
    matches = result.scalars().unique().all()

    entries = []
    for match in matches:
        # Find user's participation
        my_part = next(
            (p for p in match.participants if p.player_id == user_id), None
        )
        if not my_part:
            continue

        elo_before = my_part.elo_before
        elo_after = my_part.elo_after
        elo_change = (elo_after - elo_before) if elo_after is not None else None

        # Determine outcome using ELO change (reliable for both chess & poker)
        result_str = match.result.value if match.result else None
        if result_str == "draw":
            outcome = "draw"
        elif elo_after is not None and elo_before is not None:
            if elo_after > elo_before:
                outcome = "win"
            elif elo_after < elo_before:
                outcome = "loss"
            else:
                outcome = "draw"
        else:
            outcome = "loss"

        # Get opponent names
        opponents = []
        for p in match.participants:
            if p.player_id != user_id:
                if p.player_id:
                    # Human player — look up username
                    u = await db.get(User, p.player_id)
                    opponents.append(u.username if u else f"Seat {p.seat}")
                else:
                    opponents.append(f"Bot (Seat {p.seat})")

        entries.append(MatchHistoryEntry(
            match_id=match.id,
            game_type=match.game_type,
            result=result_str,
            your_seat=my_part.seat,
            elo_before=elo_before,
            elo_after=elo_after,
            elo_change=elo_change,
            opponents=opponents,
            started_at=match.started_at,
            ended_at=match.ended_at,
            outcome=outcome,
        ))

    return MatchHistoryResponse(matches=entries, total=total)
