"""
Simulations router — trigger bulk headless game simulations (US 6).

POST /api/simulations        → enqueue a Celery simulation job
GET  /api/simulations/{id}   → poll job status / retrieve results
GET  /api/simulations        → list all simulations for this user (in-memory)
"""
from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.rate_limiter import limiter

router = APIRouter(prefix="/api/simulations", tags=["simulations"])

# ── In-memory store: sim_id → {owner_id, task_id, meta} ──────────────────────
_simulations: dict[str, dict] = {}

VALID_GAME_TYPES = {"chess", "poker", "mahjong"}
VALID_BOT_TYPES  = {"random", "chessbot", "pokerbot", "mahjongbot"}
MAX_GAMES = 200


# ── Schemas ───────────────────────────────────────────────────────────────────

class StartSimulationRequest(BaseModel):
    game_type: str = "chess"
    bot_a: str = Field(default="random", description="Bot type for seat 1: random | chessbot | pokerbot")
    bot_b: str = Field(default="random", description="Bot type for seat 2: random | chessbot | pokerbot")
    num_games: int = Field(default=10, ge=1, le=MAX_GAMES)


class SimulationStatusResponse(BaseModel):
    simulation_id: str
    task_id: str
    state: str          # PENDING | PROGRESS | SUCCESS | FAILURE
    percent: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_task_status(task_id: str) -> dict:
    """Query Celery for the current task state."""
    try:
        from app.celery_app import celery_app
        task = celery_app.AsyncResult(task_id)
        state = task.state

        if state == "PENDING":
            return {"state": "PENDING", "percent": 0, "result": None, "error": None}
        elif state == "PROGRESS":
            meta = task.info or {}
            return {"state": "PROGRESS", "percent": meta.get("percent", 0), "result": None, "error": None}
        elif state == "SUCCESS":
            return {"state": "SUCCESS", "percent": 100, "result": task.result, "error": None}
        elif state == "FAILURE":
            return {"state": "FAILURE", "percent": 0, "result": None, "error": str(task.info)}
        else:
            return {"state": state, "percent": 0, "result": None, "error": None}
    except Exception as e:
        return {"state": "UNKNOWN", "percent": 0, "result": None, "error": str(e)}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=SimulationStatusResponse)
@limiter.limit("5/minute")
async def start_simulation(
    request: Request,
    body: StartSimulationRequest,
    user: User = Depends(require_role(UserRole.ai_developer, UserRole.admin)),
):
    """
    Enqueue a bulk simulation job.

    Returns immediately with a simulation_id and task_id for polling.
    """
    if body.game_type not in VALID_GAME_TYPES:
        raise HTTPException(422, detail=f"game_type must be one of: {', '.join(VALID_GAME_TYPES)}")
    if body.bot_a not in VALID_BOT_TYPES:
        raise HTTPException(422, detail=f"bot_a must be one of: {', '.join(VALID_BOT_TYPES)}")
    if body.bot_b not in VALID_BOT_TYPES:
        raise HTTPException(422, detail=f"bot_b must be one of: {', '.join(VALID_BOT_TYPES)}")

    simulation_id = str(uuid.uuid4())

    # Try to dispatch via Celery; fall back to synchronous execution if broker unavailable
    try:
        from app.tasks.simulations import run_bulk_simulation
        task = run_bulk_simulation.apply_async(
            kwargs={
                "simulation_id": simulation_id,
                "game_type": body.game_type,
                "bot_a": body.bot_a,
                "bot_b": body.bot_b,
                "num_games": body.num_games,
            }
        )
        task_id = task.id
        async_mode = True
    except Exception:
        # Celery/Redis not available — run synchronously and store result immediately
        from app.tasks.simulations import run_bulk_simulation
        result = run_bulk_simulation(
            simulation_id=simulation_id,
            game_type=body.game_type,
            bot_a=body.bot_a,
            bot_b=body.bot_b,
            num_games=body.num_games,
        )
        task_id = f"sync-{simulation_id}"
        async_mode = False
        _simulations[simulation_id] = {
            "owner_id": str(user.id),
            "task_id": task_id,
            "async_mode": False,
            "result": result,
            "meta": {
                "game_type": body.game_type,
                "bot_a": body.bot_a,
                "bot_b": body.bot_b,
                "num_games": body.num_games,
            },
        }
        return SimulationStatusResponse(
            simulation_id=simulation_id,
            task_id=task_id,
            state="SUCCESS",
            percent=100,
            result=result,
        )

    _simulations[simulation_id] = {
        "owner_id": str(user.id),
        "task_id": task_id,
        "async_mode": True,
        "result": None,
        "meta": {
            "game_type": body.game_type,
            "bot_a": body.bot_a,
            "bot_b": body.bot_b,
            "num_games": body.num_games,
        },
    }

    return SimulationStatusResponse(
        simulation_id=simulation_id,
        task_id=task_id,
        state="PENDING",
        percent=0,
    )


@router.get("/{simulation_id}", response_model=SimulationStatusResponse)
async def get_simulation_status(
    simulation_id: str,
    user: User = Depends(get_current_user),
):
    """Poll the status/result of a simulation by its ID."""
    sim = _simulations.get(simulation_id)
    if not sim or sim["owner_id"] != str(user.id):
        raise HTTPException(404, detail="Simulation not found")

    if not sim.get("async_mode", True):
        # Synchronous result already stored
        return SimulationStatusResponse(
            simulation_id=simulation_id,
            task_id=sim["task_id"],
            state="SUCCESS",
            percent=100,
            result=sim["result"],
        )

    status_info = _get_task_status(sim["task_id"])

    # Cache completed result
    if status_info["state"] == "SUCCESS" and status_info["result"]:
        sim["result"] = status_info["result"]

    return SimulationStatusResponse(
        simulation_id=simulation_id,
        task_id=sim["task_id"],
        **status_info,
    )


@router.get("", response_model=list[dict])
async def list_simulations(
    user: User = Depends(get_current_user),
):
    """List all simulations started by the current user (most recent first)."""
    user_sims = []
    for sim_id, sim in _simulations.items():
        if sim["owner_id"] != str(user.id):
            continue
        entry = {
            "simulation_id": sim_id,
            "task_id": sim["task_id"],
            **sim["meta"],
        }
        if not sim.get("async_mode", True):
            entry["state"] = "SUCCESS"
            entry["percent"] = 100
        else:
            s = _get_task_status(sim["task_id"])
            entry["state"] = s["state"]
            entry["percent"] = s["percent"]
        user_sims.append(entry)
    return list(reversed(user_sims))


@router.get("/{simulation_id}/download")
async def download_simulation_report(
    simulation_id: str,
    fmt: str = Query(default="json", description="Format: json | csv"),
    user: User = Depends(get_current_user),
):
    """Download the full simulation report as JSON or CSV."""
    sim = _simulations.get(simulation_id)
    if not sim or sim["owner_id"] != str(user.id):
        raise HTTPException(404, detail="Simulation not found")

    result = sim.get("result")
    if not result:
        # Try fetching from Celery
        if sim.get("async_mode"):
            s = _get_task_status(sim["task_id"])
            if s["state"] == "SUCCESS":
                result = s["result"]
                sim["result"] = result

    if not result:
        raise HTTPException(425, detail="Simulation not complete yet")

    filename = f"simulation_{simulation_id[:8]}"

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["game_num", "winner", "reason", "turns", "duration_ms"])
        for i, game in enumerate(result.get("games", []), 1):
            writer.writerow([i, game.get("winner"), game.get("reason"), game.get("turns"), game.get("duration_ms")])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )
    else:
        json_bytes = json.dumps(result, indent=2).encode("utf-8")
        return StreamingResponse(
            iter([json_bytes]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )
