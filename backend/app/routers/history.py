"""
Match history router — returns paginated history for the current user.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.match import Match, MatchMove, MatchParticipant
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

    from app.models.agent import Agent
    from sqlalchemy import or_

    # Fetch user's agent IDs
    agent_rows = await db.execute(select(Agent.id).where(Agent.owner_id == user_id))
    my_agent_ids = {row for row in agent_rows.scalars().all()}

    condition = MatchParticipant.player_id == user_id
    if my_agent_ids:
        condition = or_(condition, MatchParticipant.agent_id.in_(list(my_agent_ids)))

    # Count total matches
    count_q = (
        select(func.count())
        .select_from(MatchParticipant)
        .join(Match, MatchParticipant.match_id == Match.id)
        .where(condition)
        .where(Match.ended_at.isnot(None))
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Fetch matches
    offset = (page - 1) * per_page
    matches_q = (
        select(Match)
        .join(MatchParticipant, Match.id == MatchParticipant.match_id)
        .where(condition)
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
        # Find user's participation (directly or via agent)
        my_part = next(
            (p for p in match.participants if p.player_id == user_id or (p.agent_id and p.agent_id in my_agent_ids)), None
        )
        if not my_part:
            continue

        elo_before = my_part.elo_before
        elo_after = my_part.elo_after
        elo_change = (elo_after - elo_before) if elo_after is not None else None

        # Determine outcome using explicit terminal info or ELO change
        result_str = match.result.value if match.result else None
        if result_str == "draw":
            outcome = "draw"
        elif match.final_state and isinstance(match.final_state, dict) and "terminal" in match.final_state:
            winner_seat = match.final_state["terminal"].get("winner_seat")
            if winner_seat == my_part.seat:
                outcome = "win"
            else:
                outcome = "loss"
        elif match.game_type == "chess" and result_str and result_str.startswith("player"):
            if result_str == f"player{my_part.seat}_win":
                outcome = "win"
            else:
                outcome = "loss"
        elif elo_after is not None and elo_before is not None:
            if elo_after > elo_before:
                outcome = "win"
            elif elo_after < elo_before:
                outcome = "loss"
            else:
                outcome = "loss"  # 0 ELO diff and no terminal info available
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
                    if p.agent_id:
                        from app.models.agent import Agent
                        a = await db.get(Agent, p.agent_id)
                        opponents.append(a.name if a else f"Agent (Seat {p.seat})")
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


@router.get("/{match_id}/moves")
async def get_match_moves(
    match_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the ordered move list for a completed match.

    Only accessible to participants of the match.
    Each entry contains: turn_number, seat, move (UCI/action), san, played_at.
    """
    # Verify the requesting user participated in this match
    participant = await db.execute(
        select(MatchParticipant).where(
            MatchParticipant.match_id == match_id,
            MatchParticipant.player_id == current_user.id,
        )
    )
    if participant.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Match not found.")

    result = await db.execute(
        select(MatchMove)
        .where(MatchMove.match_id == match_id)
        .order_by(MatchMove.turn_number, MatchMove.played_at)
    )
    moves = result.scalars().all()

    return [
        {
            "turn_number": m.turn_number,
            "seat": m.seat,
            "move": (m.move_payload or {}).get("move", ""),
            "san": (m.move_payload or {}).get("san") or (m.move_payload or {}).get("move", ""),
            "played_at": m.played_at.isoformat(),
        }
        for m in moves
    ]
