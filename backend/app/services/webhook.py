"""
Webhook dispatch service.

When it's a registered agent's turn, the platform POSTs the game state
JSON to the agent's webhook_url and expects a move response within the
configured timeout.
"""

import asyncio
import logging

import httpx

log = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5.0


async def call_agent_webhook(
    webhook_url: str,
    payload: dict,
    timeout: float = WEBHOOK_TIMEOUT_SECONDS,
) -> str | None:
    """
    POST *payload* to *webhook_url* and return the move string, or None on failure.

    Expected response JSON: {"move": "<uci-or-action-string>"}
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            move = data.get("move")
            if not isinstance(move, str) or not move.strip():
                log.warning("Webhook %s returned invalid move: %r", webhook_url, data)
                return None
            return move.strip()
    except asyncio.TimeoutError:
        log.warning("Webhook %s timed out after %.1fs", webhook_url, timeout)
        return None
    except Exception as exc:  # network errors, bad JSON, etc.
        log.warning("Webhook %s error: %s", webhook_url, exc)
        return None


def build_webhook_payload(session, seat: int) -> dict:
    """
    Build the standardised webhook payload that external agents receive.

    Shape:
        {
          "game_id": "uuid",
          "game_type": "chess",
          "your_player_id": 1,
          "board_state": { ... },
          "legal_moves": ["e2e4", ...],
          "turn_number": 14,
        }
    """
    view = session.engine.get_player_view(session.state, seat)
    return {
        "game_id": str(session.match_id),
        "game_type": session.game_type,
        "your_player_id": seat,
        "board_state": view,
        "legal_moves": view.get("legal_moves", []),
        "turn_number": getattr(session.state, "_turn_number", 0),
    }
