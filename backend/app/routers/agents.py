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
    current_user: User = Depends(
        require_role(UserRole.ai_developer, UserRole.ai_agent_owner, UserRole.admin)
    ),
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
    
    # [ISSUE #10] Remove from matchmaking queue before deletion to prevent "Zombies"
    from app.routers.matchmaking import remove_entity_globally
    remove_entity_globally(agent_id)

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


# ── Decision Logs (US 7) ──────────────────────────────────────────────────────


@router.get("/{agent_id}/logs")
async def get_agent_logs(
    agent_id: uuid.UUID,
    match_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve decision logs for an agent owned by the current user.
    Optionally filter by match_id. Returns paginated results.
    """
    from sqlalchemy import select as sa_select
    from app.models.decision_log import DecisionLog

    # Verify ownership
    result = await db.execute(
        sa_select(Agent).where(Agent.id == agent_id, Agent.owner_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    query = sa_select(DecisionLog).where(DecisionLog.agent_id == agent_id)
    if match_id:
        query = query.where(DecisionLog.match_id == match_id)
    query = query.order_by(DecisionLog.logged_at.desc()).limit(limit).offset(offset)

    rows = await db.execute(query)
    logs = rows.scalars().all()

    full_detail = current_user.role in (UserRole.ai_developer, UserRole.admin)
    return [
        {
            "id": str(log.id),
            "agent_id": str(log.agent_id),
            "match_id": str(log.match_id),
            "turn_number": log.turn_number,
            "request_payload": log.request_payload if full_detail else None,
            "response_payload": log.response_payload if full_detail else None,
            "exception": log.exception,
            "logged_at": log.logged_at.isoformat(),
        }
        for log in logs
    ]


@router.get("/{agent_id}/logs/download")
async def download_agent_logs(
    agent_id: uuid.UUID,
    match_id: Optional[uuid.UUID] = None,
    fmt: str = "json",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download all decision logs for an agent as JSON or CSV.
    Optionally filter by match_id.
    """
    import csv
    import io
    import json as json_lib
    from fastapi.responses import StreamingResponse
    from sqlalchemy import select as sa_select
    from app.models.decision_log import DecisionLog

    result = await db.execute(
        sa_select(Agent).where(Agent.id == agent_id, Agent.owner_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    query = sa_select(DecisionLog).where(DecisionLog.agent_id == agent_id)
    if match_id:
        query = query.where(DecisionLog.match_id == match_id)
    query = query.order_by(DecisionLog.logged_at.asc())

    rows = await db.execute(query)
    logs = rows.scalars().all()

    filename = f"decision_logs_{str(agent_id)[:8]}"

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "match_id", "turn_number", "move_sent", "exception", "logged_at"])
        for log in logs:
            move = (log.response_payload or {}).get("move", "")
            writer.writerow([
                str(log.id), str(log.match_id), log.turn_number,
                move, log.exception or "", log.logged_at.isoformat()
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )
    else:
        data = [
            {
                "id": str(log.id),
                "match_id": str(log.match_id),
                "turn_number": log.turn_number,
                "request_payload": log.request_payload,
                "response_payload": log.response_payload,
                "exception": log.exception,
                "logged_at": log.logged_at.isoformat(),
            }
            for log in logs
        ]
        json_bytes = json_lib.dumps(data, indent=2).encode("utf-8")
        return StreamingResponse(
            iter([json_bytes]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )
