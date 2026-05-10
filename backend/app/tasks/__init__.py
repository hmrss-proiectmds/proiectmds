"""
Celery tasks for bulk headless game simulation (US 6).

A bulk simulation runs N games between two agents/bots completely
headlessly — no WebSocket delays, no artificial pauses — and returns
a statistical summary report.
"""
from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.celery_app import celery_app


def _run_single_game(
    game_type: str,
    bot_a: str,
    bot_b: str,
    max_turns: int = 500,
) -> dict:
    """
    Run one complete headless game between two bots.
    Returns a result dict: {winner, reason, turns, duration_ms}
    """
    import time
    from app.games.registry import get_engine
    from app.games.bots.random_bot import pick_random_move

    engine = get_engine(game_type)

    # Poker needs num_players arg
    if game_type == "poker":
        state = engine.create_initial_state(num_players=3)
    else:
        state = engine.create_initial_state()

    def pick_move(bot_type: str, st) -> Optional[str]:
        """Pick a move for the given bot type."""
        if bot_type == "random":
            return pick_random_move(engine, st)
        elif bot_type == "chessbot" and game_type == "chess":
            try:
                from app.games.bots.hf_chessbot import pick_hf_move
                return pick_hf_move(engine, st, temperature=0.5)
            except Exception:
                return pick_random_move(engine, st)
        elif bot_type == "pokerbot" and game_type == "poker":
            try:
                from app.games.bots.hf_pokerbot import pick_hf_poker_move
                return pick_hf_poker_move(engine, st)
            except Exception:
                return pick_random_move(engine, st)
        return pick_random_move(engine, st)

    t0 = time.monotonic()
    turns = 0
    bots = {1: bot_a, 2: bot_b}

    while turns < max_turns:
        terminal = engine.is_terminal(state)
        if terminal:
            break

        # For poker: handle hand transitions automatically
        if game_type == "poker" and hasattr(engine, "needs_new_hand"):
            if engine.needs_new_hand(state):
                terminal = engine.is_terminal(state)
                if terminal:
                    break
                state = engine.start_next_hand(state)
                continue

        current = engine.get_current_turn(state)
        bot_type = bots.get(current % 2 + 1 if current not in bots else current, "random")
        # for multiplayer poker, seats 3+ use bot_b
        if current not in bots:
            bot_type = bot_b

        legal = engine.get_legal_moves(state)
        if not legal:
            break

        move = pick_move(bot_type, state)
        if not move:
            break
        try:
            state = engine.apply_move(state, move)
        except Exception:
            break
        turns += 1

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    terminal = engine.is_terminal(state)

    return {
        "winner": terminal.get("result") if terminal else "unknown",
        "reason": terminal.get("reason") if terminal else "max_turns",
        "turns": turns,
        "duration_ms": elapsed_ms,
    }


@celery_app.task(bind=True, name="simulations.run_bulk")
def run_bulk_simulation(
    self,
    simulation_id: str,
    game_type: str,
    bot_a: str,
    bot_b: str,
    num_games: int,
) -> dict:
    """
    Celery task: run `num_games` headless games and return a summary report.

    Progress is reported via task state so the frontend can poll it.
    """
    results = []
    errors = 0

    for i in range(num_games):
        # Report progress
        self.update_state(
            state="PROGRESS",
            meta={
                "simulation_id": simulation_id,
                "completed": i,
                "total": num_games,
                "percent": int(i / num_games * 100),
            },
        )
        try:
            r = _run_single_game(game_type, bot_a, bot_b)
            results.append(r)
        except Exception as exc:
            errors += 1
            results.append({"winner": "error", "reason": str(exc), "turns": 0, "duration_ms": 0})

    # Compile statistics
    wins_a = sum(1 for r in results if r["winner"] in ("player1_win",))
    wins_b = sum(1 for r in results if r["winner"] in ("player2_win",))
    draws = sum(1 for r in results if r["winner"] == "draw")
    total_done = len(results)
    avg_turns = sum(r["turns"] for r in results) / max(total_done, 1)
    avg_ms = sum(r["duration_ms"] for r in results) / max(total_done, 1)

    return {
        "simulation_id": simulation_id,
        "game_type": game_type,
        "bot_a": bot_a,
        "bot_b": bot_b,
        "num_games": num_games,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "wins_a": wins_a,
            "wins_b": wins_b,
            "draws": draws,
            "errors": errors,
            "win_rate_a": round(wins_a / max(total_done, 1), 4),
            "win_rate_b": round(wins_b / max(total_done, 1), 4),
            "avg_turns": round(avg_turns, 1),
            "avg_duration_ms": round(avg_ms, 1),
        },
        "games": results,
    }
