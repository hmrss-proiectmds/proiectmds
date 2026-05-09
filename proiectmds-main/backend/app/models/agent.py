"""
Agent ORM model — represents an AI agent registered on the platform.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IntegrationMode(str, enum.Enum):
    webhook = "webhook"
    upload = "upload"


class AgentStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    banned = "banned"


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    game_type: Mapped[str] = mapped_column(String(50), nullable=False)
    integration_mode: Mapped[IntegrationMode] = mapped_column(
        Enum(IntegrationMode), nullable=False, default=IntegrationMode.webhook
    )
    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    script_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    elo_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    continuous_queue: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), nullable=False, default=AgentStatus.active
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner = relationship("User", back_populates="agents")
