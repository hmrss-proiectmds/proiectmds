"""
Agents router — upload and list AI agent scripts.
"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_agent(
    name: str = Form(..., min_length=1, max_length=100),
    game_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.ai_developer, UserRole.ai_agent_owner, UserRole.admin)),
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

    # Persist agent record
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

    return {
        "id": str(agent.id),
        "name": agent.name,
        "game_type": agent.game_type,
        "status": agent.status,
        "elo_rating": agent.elo_rating,
        "created_at": agent.created_at.isoformat(),
    }


@router.patch("/{agent_id}/rename", status_code=status.HTTP_200_OK)
async def rename_agent(
    agent_id: str,
    name: str = Form(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename an agent owned by the current user."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    result = await db.execute(
        select(Agent).where(Agent.id == agent_uuid, Agent.owner_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    agent.name = name
    await db.commit()
    await db.refresh(agent)
    return {"id": str(agent.id), "name": agent.name}


@router.get("/")
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all agents owned by the current user."""
    result = await db.execute(
        select(Agent).where(Agent.owner_id == current_user.id).order_by(Agent.created_at.desc())
    )
    agents = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "game_type": a.game_type,
            "status": a.status,
            "elo_rating": a.elo_rating,
            "created_at": a.created_at.isoformat(),
        }
        for a in agents
    ]
