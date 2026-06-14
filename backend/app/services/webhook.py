"""
Webhook dispatch service.

When it's a registered agent's turn, the platform POSTs the game state
JSON to the agent's webhook_url and expects a move response within the
configured timeout.

Rate limiting: each agent owner is capped at RATE_LIMIT_MAX_CALLS calls
within a RATE_LIMIT_WINDOW_SECONDS rolling window.  Calls that exceed the
cap return None immediately (same as a timeout) so the game engine falls back
to a random move without blocking the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Deque

import httpx

log = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5.0

# ── Rate-limiting configuration ────────────────────────────────────────────────
RATE_LIMIT_WINDOW_SECONDS = 60      # rolling window length in seconds
RATE_LIMIT_MAX_CALLS = 30           # max calls per owner per window

# owner_id (str) → deque of call timestamps (float, epoch seconds)
_rate_counters: dict[str, Deque[float]] = defaultdict(deque)


def _check_rate_limit(owner_id: str) -> bool:
    """Return True if the owner is within the rate limit, False if exceeded."""
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    dq = _rate_counters[owner_id]

    # Evict timestamps outside the rolling window
    while dq and dq[0] < window_start:
        dq.popleft()

    if len(dq) >= RATE_LIMIT_MAX_CALLS:
        log.warning(
            "Webhook rate limit exceeded for owner %s: %d calls in last %ds",
            owner_id,
            len(dq),
            RATE_LIMIT_WINDOW_SECONDS,
        )
        return False

    dq.append(now)
    return True


async def call_agent_webhook(
    webhook_url: str,
    payload: dict,
    timeout: float = WEBHOOK_TIMEOUT_SECONDS,
    owner_id: str = "",
) -> str | None:
    """
    POST *payload* to *webhook_url* and return the move string, or None on failure.

    Expected response JSON: {"move": "<uci-or-action-string>"}

    Args:
        webhook_url: The agent's registered callback URL.
        payload:     Standardised game-state dictionary.
        timeout:     Per-request timeout in seconds (default 5 s).
        owner_id:    Unique owner identifier used for rate limiting.
                     Pass an empty string to skip rate limiting.
    """
    if owner_id and not _check_rate_limit(owner_id):
        return None

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
