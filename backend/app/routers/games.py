"""
Games router — REST endpoints for game CRUD + WebSocket for live play.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.game import (
    CreateGameRequest,
    GameResponse,
    GameStateResponse,
    OpenGameResponse,
    PlayerInfo,
)
from app.services.auth import decode_access_token, get_user_by_id
from app.services.game import game_manager
from app.websocket.manager import manager as ws_manager

router = APIRouter(prefix="/api/games", tags=["games"])


# ── Helpers ──

def _session_to_response(session) -> GameResponse:
    return GameResponse(
        game_id=session.match_id,
        game_type=session.game_type,
        status=session.status,
        players=[
            PlayerInfo(**p.to_dict()) for p in session.players.values()
        ],
        created_at=session.created_at,
    )


def _build_state_response(session, seat: int) -> dict:
    view = session.engine.get_player_view(session.state, seat)
    players = [PlayerInfo(**p.to_dict()) for p in session.players.values()]
    return {
        "type": "game_state",
        "game_id": str(session.match_id),
        "status": session.status,
        "your_seat": seat,
        "players": [p.model_dump(mode="json") for p in players],
        **view,
    }


# ── REST Endpoints ──


@router.post("", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    body: CreateGameRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new game. Set vs_ai=true and choose bot_type ('random' or 'chessbot')."""
    session = await game_manager.create_game(
        db=db,
        game_type=body.game_type,
        creator_id=user.id,
        creator_username=user.username,
        creator_elo=user.elo_rating,
        vs_ai=body.vs_ai,
        bot_type=body.bot_type,
    )
    return _session_to_response(session)


@router.get("/open", response_model=OpenGameResponse)
async def list_open_games(user: User = Depends(get_current_user)):
    """List games waiting for a second player."""
    sessions = game_manager.get_open_games()
    return OpenGameResponse(
        games=[_session_to_response(s) for s in sessions]
    )


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: uuid.UUID,
    user: User = Depends(get_current_user),
):
    """Get game info by ID."""
    session = game_manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")
    return _session_to_response(session)


@router.post("/{game_id}/join", response_model=GameResponse)
async def join_game(
    game_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join an open game as the second player."""
    try:
        session = await game_manager.join_game(
            db=db,
            match_id=game_id,
            player_id=user.id,
            player_username=user.username,
            player_elo=user.elo_rating,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Notify player 1 that someone joined
    state_msg = _build_state_response(session, seat=1)
    await ws_manager.send_to_player(game_id, 1, state_msg)

    return _session_to_response(session)


@router.post("/{game_id}/resign")
async def resign_game(
    game_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resign the current game."""
    seat = game_manager.get_player_seat(game_id, user.id)
    if seat is None:
        raise HTTPException(status_code=403, detail="You are not in this game")
    try:
        session = await game_manager.resign(db, game_id, seat)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Broadcast final state to all
    for s in session.players:
        msg = _build_state_response(session, s)
        await ws_manager.send_to_player(game_id, s, msg)

    return {"detail": "Resigned", "result": session.result}


# ── WebSocket ──


@router.websocket("/ws/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: uuid.UUID):
    """
    Live game WebSocket.
    Connect with ?token=<JWT>.
    Send: {"type": "move", "move": "e2e4"} or {"type": "resign"}
    Receive: game_state messages after each move.
    """
    # ── Auth from query param ──
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Missing token"})
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Invalid token"})
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = uuid.UUID(payload["sub"])

    # ── Find session and seat ──
    session = game_manager.get_session(game_id)
    if not session:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Game not found"})
        await websocket.close(code=4004, reason="Game not found")
        return

    seat = game_manager.get_player_seat(game_id, user_id)
    if seat is None:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Not a participant"})
        await websocket.close(code=4003, reason="Not a participant")
        return

    # ── Connect (accept + register) ──
    await ws_manager.connect_player(game_id, seat, websocket)

    # Send initial state
    state_msg = _build_state_response(session, seat)
    await websocket.send_json(state_msg)

    # ── Message loop ──
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "move":
                await _handle_move(websocket, game_id, seat, data.get("move", ""))

            elif msg_type == "resign":
                await _handle_resign(websocket, game_id, seat)
                break

            else:
                await websocket.send_json({
                    "type": "error", "message": f"Unknown message type: {msg_type}"
                })

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect_player(game_id, seat)


async def _handle_move(ws: WebSocket, game_id: uuid.UUID, seat: int, move_uci: str):
    """Process a move from a WebSocket client."""
    from app.database import async_session

    async with async_session() as db:
        try:
            session, move_info = await game_manager.make_move(db, game_id, seat, move_uci)
            await db.commit()
        except ValueError as e:
            await ws.send_json({"type": "error", "message": str(e)})
            return

        # Send updated state to all players
        for s in session.players:
            msg = _build_state_response(session, s)
            await ws_manager.send_to_player(game_id, s, msg)

        # If vs AI and it's the bot's turn, make the AI move
        if session.status == "active":
            async with async_session() as db2:
                ai_result = await game_manager.make_ai_move(db2, game_id)
                if ai_result:
                    await db2.commit()
                    session, _ = ai_result
                    for s in session.players:
                        msg = _build_state_response(session, s)
                        await ws_manager.send_to_player(game_id, s, msg)


async def _handle_resign(ws: WebSocket, game_id: uuid.UUID, seat: int):
    """Process a resignation from a WebSocket client."""
    from app.database import async_session

    async with async_session() as db:
        try:
            session = await game_manager.resign(db, game_id, seat)
            await db.commit()
        except ValueError as e:
            await ws.send_json({"type": "error", "message": str(e)})
            return

        for s in session.players:
            msg = _build_state_response(session, s)
            await ws_manager.send_to_player(game_id, s, msg)
