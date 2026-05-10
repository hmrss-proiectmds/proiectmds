"""
WebSocket connection manager.
Tracks per-game player and spectator connections and handles broadcasting.
"""

from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    """In-memory WebSocket connection tracker."""

    def __init__(self):
        # game_id -> seat -> WebSocket
        self.players: dict[UUID, dict[int, WebSocket]] = {}
        # game_id -> [WebSocket]
        self.spectators: dict[UUID, list[WebSocket]] = {}

    async def connect_player(self, game_id: UUID, seat: int, ws: WebSocket) -> None:
        await ws.accept()
        self.players.setdefault(game_id, {})[seat] = ws

    async def connect_spectator(self, game_id: UUID, ws: WebSocket) -> None:
        await ws.accept()
        self.spectators.setdefault(game_id, []).append(ws)

    def disconnect_player(self, game_id: UUID, seat: int) -> None:
        conns = self.players.get(game_id)
        if conns:
            conns.pop(seat, None)
            if not conns:
                del self.players[game_id]

    def disconnect_spectator(self, game_id: UUID, ws: WebSocket) -> None:
        specs = self.spectators.get(game_id)
        if specs:
            try:
                specs.remove(ws)
            except ValueError:
                pass
            if not specs:
                del self.spectators[game_id]

    def get_player_ws(self, game_id: UUID, seat: int) -> WebSocket | None:
        return self.players.get(game_id, {}).get(seat)

    async def send_to_player(self, game_id: UUID, seat: int, data: dict) -> None:
        ws = self.get_player_ws(game_id, seat)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect_player(game_id, seat)

    async def broadcast(self, game_id: UUID, data: dict) -> None:
        """Send to all connected players and spectators for a game."""
        for seat, ws in list(self.players.get(game_id, {}).items()):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect_player(game_id, seat)

        for ws in list(self.spectators.get(game_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect_spectator(game_id, ws)

    async def send_personal_state(
        self, game_id: UUID, seat: int, view: dict, status: str
    ) -> None:
        """Send a personalized game_state message to a specific player."""
        msg = {"type": "game_state", "status": status, **view}
        await self.send_to_player(game_id, seat, msg)

    def cleanup_game(self, game_id: UUID) -> None:
        self.players.pop(game_id, None)
        self.spectators.pop(game_id, None)


# Module-level singleton
manager = ConnectionManager()
