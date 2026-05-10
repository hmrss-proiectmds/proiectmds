"""
Match, MatchParticipant, and MatchMove ORM models.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MatchResult(str, enum.Enum):
    player1_win = "player1_win"
    player2_win = "player2_win"
    draw = "draw"


class MatchMode(str, enum.Enum):
    live = "live"
    bulk = "bulk"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_type: Mapped[str] = mapped_column(String(50), nullable=False)
    final_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[MatchResult | None] = mapped_column(
        Enum(MatchResult), nullable=True
    )
    mode: Mapped[MatchMode] = mapped_column(
        Enum(MatchMode), nullable=False, default=MatchMode.live
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    participants = relationship("MatchParticipant", back_populates="match")
    moves = relationship("MatchMove", back_populates="match")


class MatchParticipant(Base):
    __tablename__ = "match_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True
    )
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    seat: Mapped[int] = mapped_column(Integer, nullable=False)
    elo_before: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    elo_after: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    match = relationship("Match", back_populates="participants")


class MatchMove(Base):
    __tablename__ = "match_moves"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seat: Mapped[int] = mapped_column(Integer, nullable=False)
    board_state_before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    move_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    match = relationship("Match", back_populates="moves")
