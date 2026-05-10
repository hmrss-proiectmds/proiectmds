"""
Celery tasks for bulk headless game simulation (US 6).
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.celery_app import celery_app
from app.games.bots.random_bot import pick_random_move
try:
    from app.games.bots.hf_chessbot import pick_hf_move
except ImportError:
    pick_hf_move = None
try:
    from app.games.bots.hf_pokerbot import pick_hf_poker_move
except ImportError:
    pick_hf_poker_move = None


def _run_single_game(game_type: str, bot_a: str, bot_b: str, max_turns: int = 500) -> dict:
    """Run one complete headless game between two bots."""
    from app.games.registry import get_engine

    engine = get_engine(game_type)
    state = engine.create_initial_state(num_players=3) if game_type == "poker" else engine.create_initial_state()

    def pick_move(bot_type: str, st):
        if bot_type == "random":
            return pick_random_move(engine, st)
        elif bot_type == "chessbot" and game_type == "chess":
            if pick_hf_move:
                try:
                    return pick_hf_move(engine, st, temperature=0.5)
                except Exception as e:
                    print(f"BOT ERROR (Chess): {e}")
                    return pick_random_move(engine, st)
            return pick_random_move(engine, st)
        elif bot_type == "pokerbot" and game_type == "poker":
            if pick_hf_poker_move:
                try:
                    return pick_hf_poker_move(engine, st)
                except Exception as e:
                    print(f"BOT ERROR (Poker): {e}")
                    return pick_random_move(engine, st)
            return pick_random_move(engine, st)
        return pick_random_move(engine, st)

    t0 = time.monotonic()
    turns = 0

    while turns < max_turns:
        terminal = engine.is_terminal(state)
        if terminal:
            break

        if game_type == "poker" and hasattr(engine, "needs_new_hand") and engine.needs_new_hand(state):
            terminal = engine.is_terminal(state)
            if terminal:
                break
            state = engine.start_next_hand(state)
            continue

        legal = engine.get_legal_moves(state)
        if not legal:
            break

        current = engine.get_current_turn(state)
        # Seat 1 = bot_a, all others = bot_b
        bot_type = bot_a if current == 1 else bot_b

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
        "reason": terminal.get("reason") if terminal else "max_turns_reached",
        "turns": turns,
        "duration_ms": elapsed_ms,
    }


@celery_app.task(bind=True, name="simulations.run_bulk")
def run_bulk_simulation(self, simulation_id: str, game_type: str, bot_a: str, bot_b: str, num_games: int) -> dict:
    """
    Run `num_games` headless games between bot_a (seat 1) and bot_b (seat 2+).
    Progress is streamed via Celery task state so the frontend can poll it.
    """
    results = []
    errors = 0

    for i in range(num_games):
        # Only update Celery state if we are running as a task
        if hasattr(self, "update_state"):
            self.update_state(
                state="PROGRESS",
                meta={"simulation_id": simulation_id, "completed": i, "total": num_games, "percent": int(i / num_games * 100)},
            )
        try:
            r = _run_single_game(game_type, bot_a, bot_b)
            results.append(r)
        except Exception as exc:
            errors += 1
            results.append({"winner": "error", "reason": str(exc), "turns": 0, "duration_ms": 0})

    total_done = len(results)
    
    # Accurate win counting for multi-player games (like 3-player poker)
    # player1 = bot_a
    # player2, player3, ... = bot_b
    wins_a = sum(1 for r in results if r.get("winner") == "player1_win")
    
    # wins_b should be anything that is a player win but NOT player 1
    wins_b = sum(1 for r in results if r.get("winner", "").startswith("player") 
                 and r.get("winner") != "player1_win")
    
    draws   = sum(1 for r in results if r.get("winner") == "draw")
    
    # Calculate averages, avoiding division by zero
    valid_games = [r for r in results if r.get("winner") not in ("error", "unknown")]
    num_valid = len(valid_games)
    
    avg_turns = sum(r["turns"] for r in valid_games) / max(num_valid, 1)
    avg_ms    = sum(r["duration_ms"] for r in results) / max(total_done, 1)

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
            "win_rate_a": round(wins_a / max(total_done - draws - errors, 1), 4),
            "win_rate_b": round(wins_b / max(total_done - draws - errors, 1), 4),
            "avg_turns": round(avg_turns, 1),
            "avg_duration_ms": round(avg_ms, 1),
        },
        "games": results,
    }
