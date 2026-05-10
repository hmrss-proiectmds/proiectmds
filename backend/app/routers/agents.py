"""
Agents router — register webhook agents, upload Python scripts, list and manage agents.
"""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.agent import Agent, IntegrationMode
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Directory where uploaded agent scripts are stored
AGENTS_DIR = Path("uploaded_agents")
ALLOWED_EXTENSIONS = {".py"}
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB
ALLOWED_GAME_TYPES = {"chess", "poker"}


def _safe_filename(filename: str) -> str:
    """Strip directory components and keep only the base filename."""
    return Path(filename).name


# ── Schemas ───────────────────────────────────────────────────────────────────


class RegisterWebhookRequest(BaseModel):
    name: str
    game_type: str = "chess"
    webhook_url: str  # validated as non-empty URL string
    continuous_queue: bool = False


class UpdateAgentRequest(BaseModel):
    continuous_queue: Optional[bool] = None
    webhook_url: Optional[str] = None


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    game_type: str
    integration_mode: str
    webhook_url: Optional[str]
    elo_rating: int
    status: str
    continuous_queue: bool
    created_at: str
    in_game_id: Optional[str] = None
    in_queue: bool = False

    @classmethod
    def from_orm(cls, a: Agent) -> "AgentResponse":
        return cls(
            id=a.id,
            name=a.name,
            game_type=a.game_type,
            integration_mode=a.integration_mode.value,
            webhook_url=a.webhook_url,
            elo_rating=a.elo_rating,
            status=a.status.value,
            continuous_queue=a.continuous_queue,
            created_at=a.created_at.isoformat(),
        )


# ── Webhook registration ───────────────────────────────────────────────────────


@router.post("/register-webhook", status_code=status.HTTP_201_CREATED, response_model=AgentResponse)
async def register_webhook_agent(
    body: RegisterWebhookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a webhook-mode agent.

    The platform will POST game state JSON to *webhook_url* whenever it's
    this agent's turn. The endpoint must respond with {"move": "<string>"}.
    """
    if body.game_type not in ALLOWED_GAME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"game_type must be one of: {', '.join(sorted(ALLOWED_GAME_TYPES))}",
        )
    if not body.webhook_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="webhook_url must start with http:// or https://",
        )

    agent = Agent(
        owner_id=current_user.id,
        name=body.name,
        game_type=body.game_type,
        integration_mode=IntegrationMode.webhook,
        webhook_url=body.webhook_url,
        continuous_queue=body.continuous_queue,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.from_orm(agent)


# ── Script upload ─────────────────────────────────────────────────────────────


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=AgentResponse)
async def upload_agent(
    name: str = Form(..., min_length=1, max_length=100),
    game_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(
        require_role(UserRole.ai_developer, UserRole.ai_agent_owner, UserRole.admin)
    ),
    db: AsyncSession = Depends(get_db),
):
    """Upload a Python agent script and register it in the database."""
    if game_type not in ALLOWED_GAME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"game_type must be one of: {', '.join(sorted(ALLOWED_GAME_TYPES))}",
        )

    safe_name = _safe_filename(file.filename or "agent.py")
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only .py files are accepted.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 1 MB limit.",
        )

    # Save file to disk
    AGENTS_DIR.mkdir(exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    dest = AGENTS_DIR / unique_name
    dest.write_bytes(contents)

    agent = Agent(
        owner_id=current_user.id,
        name=name,
        game_type=game_type,
        integration_mode=IntegrationMode.upload,
        script_path=str(dest),
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.from_orm(agent)


# ── Update agent settings ─────────────────────────────────────────────────────


@router.patch("/{agent_id}", status_code=status.HTTP_200_OK, response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    body: UpdateAgentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update agent settings: webhook_url and/or continuous_queue toggle."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    if body.continuous_queue is not None:
        agent.continuous_queue = body.continuous_queue
    if body.webhook_url is not None:
        if body.webhook_url and not body.webhook_url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=422,
                detail="webhook_url must start with http:// or https://",
            )
        agent.webhook_url = body.webhook_url or None

    await db.commit()
    await db.refresh(agent)
    return AgentResponse.from_orm(agent)


# ── Rename ────────────────────────────────────────────────────────────────────


@router.patch("/{agent_id}/rename", status_code=status.HTTP_200_OK)
async def rename_agent(
    agent_id: uuid.UUID,
    name: str = Form(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename an agent owned by the current user."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    agent.name = name
    await db.commit()
    await db.refresh(agent)
    return {"id": str(agent.id), "name": agent.name}


# ── Delete ────────────────────────────────────────────────────────────────────


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an agent owned by the current user."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.owner_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    await db.delete(agent)
    await db.commit()


# ── List ──────────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[AgentResponse])
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all agents owned by the current user."""
    result = await db.execute(
        select(Agent).where(Agent.owner_id == current_user.id).order_by(Agent.created_at.desc())
    )
    agents = result.scalars().all()

    from app.services.game import game_manager
    from app.routers.matchmaking import _queues

    responses = []
    for a in agents:
        resp = AgentResponse.from_orm(a)
        
        # Check if in queue
        q = _queues.get(a.game_type, [])
        resp.in_queue = any(e.entity_id == a.id for e in q)
        
        # Check if in an active game
        for session in game_manager.sessions.values():
            if session.status == "active":
                for slot in session.players.values():
                    if slot.is_ai and slot.agent_id == a.id:
                        resp.in_game_id = str(session.match_id)
                        break
            if resp.in_game_id:
                break
                
        responses.append(resp)

    return responses
