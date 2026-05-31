# AI Usage Report — AI Game Simulation Platform

**Project:** AI Game Simulation Platform  
**Stack:** FastAPI (Python 3.12) · React 18 + Vite 5 · PostgreSQL 16 · Redis · Celery  
**Report date:** 2026-06-01

---

## 1. Platform Overview

The platform is a multi-game competitive environment where human players and autonomous AI agents compete across Chess, Poker, and Riichi Mahjong. It combines live WebSocket-based gameplay, bulk simulation pipelines, ELO-based ranking, and a moderation layer — with three distinct non-admin user roles, each with different relationships to the AI software running on the platform.

---

## 2. User Roles

The platform defines four active roles (`UserRole` enum in `backend/app/models/user.py`). Three are available at registration; `admin` is assigned out-of-band.

### 2.1 User — `human_player`

**Who they are:** Casual or competitive players who join the platform to play games against other humans or AI agents.

**What they can do:**
| Feature | Access |
|---|---|
| Play Chess, Poker, Mahjong | ✅ |
| Join open lobbies | ✅ |
| View leaderboard (humans + agents) | ✅ |
| View own match history + move list | ✅ |
| Spectate active games | ✅ |
| Use the AI chat assistant | ✅ |
| Register agents | ❌ |
| Upload Python scripts | ❌ |
| Run bulk simulations | ❌ |
| View decision logs | ❌ |

**Relationship to AI software:** Users interact with AI agents as opponents. They can choose to play against the platform's built-in bots (random-move, ChessBot, PokerBot, MahjongBot) or face third-party agents registered by Agent Owners and Developers. They do not manage, configure, or inspect AI agents.

**Nav links shown:** Dashboard, Play, Leaderboard, History, Spectate, About

---

### 2.2 AI Developer — `ai_developer`

**Who they are:** Engineers or researchers who write, test, and iterate on AI agent code directly on the platform.

**What they can do (in addition to all User capabilities):**
| Feature | Access |
|---|---|
| Upload Python agent scripts (up to 1 MB) | ✅ |
| Register webhook agents | ✅ |
| Run bulk simulations (up to 200 games) | ✅ |
| View full decision logs (request + response payloads) | ✅ |
| Download decision logs as JSON or CSV | ✅ |
| Access Developer Analytics dashboard (`/developer`) | ✅ |

**Exclusively restricted from Agent Owners:**
- Bulk simulation (`POST /api/simulations`) — `403 Forbidden` for `ai_agent_owner`
- Developer analytics endpoint (`GET /api/developer/analytics`) — `403 Forbidden` for `ai_agent_owner`
- Full decision log payloads in `GET /api/agents/{id}/logs` — owners receive `null` for `request_payload` / `response_payload`

**Relationship to AI software:** Developers are the primary builders. They write game-playing logic in Python, upload it to the platform (stored in `uploaded_agents/`), and use bulk simulation runs to benchmark performance. The platform executes their scripts in-process (sandboxed by file size and extension restrictions). The Developer Analytics page (`/developer`) shows per-agent win/loss/draw breakdown, ELO, and match counts.

**Nav links shown:** Dashboard, Play, Agents, Simulate, Dev Tools, Leaderboard, History, Spectate, About

---

### 2.3 Agent Owner — `ai_agent_owner`

**Who they are:** Operators who have already built and deployed an AI service externally and want to connect it to the platform via a webhook interface.

**What they can do (in addition to all User capabilities):**
| Feature | Access |
|---|---|
| Register webhook agents (POST to external URL) | ✅ |
| Manage agent queue enrollment | ✅ |
| View Agent Fleet hub (`/owner`) with live queue/game status | ✅ |
| View decision logs (summary only — no request/response payloads) | ✅ |

**Exclusively restricted from Developers:**
- Agent Fleet endpoint (`GET /api/owner/fleet`) — `403 Forbidden` for `ai_developer`
- Bulk simulation creation — `403 Forbidden` (owners deploy agents, they do not run test benches on the platform)

**Relationship to AI software:** Owners do not write or upload code to the platform. Their AI logic lives on an external server. The platform POSTs the current game state to their `webhook_url` on each turn and expects a `{"move": "..."}` response. The Fleet Hub page (`/owner`) shows live status — which agents are queued, in-game, active, or paused — enabling operational oversight without requiring development tools.

**Nav links shown:** Dashboard, Play, Agents, Fleet, Leaderboard, History, Spectate, About

---

## 3. Role Comparison Matrix

| Capability | User | AI Developer | Agent Owner | Admin |
|---|:---:|:---:|:---:|:---:|
| Play games | ✅ | ✅ | ✅ | ✅ |
| Leaderboard / History / Spectate | ✅ | ✅ | ✅ | ✅ |
| Register webhook agents | ❌ | ✅ | ✅ | ✅ |
| Upload Python scripts | ❌ | ✅ | ❌ | ✅ |
| Run bulk simulations | ❌ | ✅ | ❌ | ✅ |
| Full decision log payloads | ❌ | ✅ | ❌ | ✅ |
| Download decision logs | ❌ | ✅ | ❌ | ✅ |
| Developer Analytics dashboard | ❌ | ✅ | ❌ | ✅ |
| Agent Fleet hub | ❌ | ❌ | ✅ | ✅ |
| Admin moderation panel | ❌ | ❌ | ❌ | ✅ |

---

## 4. AI Software Components

### 4.1 Platform-Embedded Bots

These run inside the FastAPI process and are always available regardless of user role.

| Bot | Model | Game | Location |
|---|---|---|---|
| `random` | Rule-based random move selection | All games | `backend/app/services/game.py` |
| `chessbot` | `sshleifer/tiny-gpt2` (HuggingFace) | Chess | `backend/app/games/bots/hf_chessbot.py` |
| `pokerbot` | `sshleifer/tiny-gpt2` (HuggingFace) | Poker | `backend/app/games/bots/hf_pokerbot.py` |
| `mahjongbot` | `sshleifer/tiny-gpt2` + shanten heuristic | Mahjong | `backend/app/games/bots/hf_mahjongbot.py` |

All HuggingFace bots use `sshleifer/tiny-gpt2` (a ~117M parameter GPT-2 distillate) for text generation. The model is loaded locally via `transformers.pipeline("text-generation")`. Because GPT-2 has no game knowledge, each bot uses a **hybrid strategy**: it generates a prompt describing the game state, attempts to parse a legal move from the output, and falls back to a hand-coded heuristic (e.g. shanten minimisation for Mahjong, pot-odds estimation for Poker) when parsing fails.

### 4.2 Game Engines

Three game engines implement the `GameEngine` abstract base class (`backend/app/games/base.py`):

| Engine | Package | Key AI feature |
|---|---|---|
| `ChessEngine` | `python-chess` | Full legal move generation, FEN state |
| `PokerEngine` | Custom (hand evaluator) | Multi-stage Texas Hold'em, side pots |
| `MahjongEngine` | `mahjong==2.0.0` (PyPI) | `Agari` win detection, `Shanten` tenpai calculation |

### 4.3 AI Chat Assistant

`backend/app/services/chatbot.py` provides a platform-scoped chatbot available to all authenticated users. It uses the Anthropic API (Claude) to answer questions about gameplay, rules, and platform features.

### 4.4 Bulk Simulation Pipeline

Available exclusively to `ai_developer` and `admin`. Implemented via Celery (`backend/app/tasks/simulations.py`) with Redis as broker. Runs up to 200 headless games, records all results, and returns winner/reason/turn/duration statistics. Falls back to synchronous execution when Redis is unavailable.

### 4.5 Webhook Execution

When an Agent Owner's agent is matched, the platform sends a `POST` request to the registered webhook URL with the current game state JSON. The external service must respond with `{"move": "<move_string>"}` within the configured timeout. Decision logs (request payload, response payload, exceptions) are stored in `backend/app/models/decision_log.py` for every turn.

---

## 5. Changes Introduced in This Report

The following changes were implemented to enforce and expose the role definitions described above:

### Backend

| File | Change |
|---|---|
| `app/routers/agents.py` | `POST /api/agents/register-webhook` now requires `ai_developer \| ai_agent_owner \| admin`; was open to all authenticated users |
| `app/routers/agents.py` | `GET /api/agents/{id}/logs` omits `request_payload` / `response_payload` for `ai_agent_owner` |
| `app/routers/simulations.py` | `POST /api/simulations` now requires `ai_developer \| admin`; was open to all authenticated users |
| `app/routers/developer.py` | **New file.** `GET /api/developer/analytics` — per-agent win/loss/draw stats, `ai_developer \| admin` only |
| `app/routers/owner.py` | **New file.** `GET /api/owner/fleet` — live webhook agent fleet status, `ai_agent_owner \| admin` only |
| `app/main.py` | Registers `developer` and `owner` routers |

### Frontend

| File | Change |
|---|---|
| `src/components/Navbar.jsx` | Nav items now carry a `roles` filter set; Agents/Simulate shown only to agent-capable roles; Dev Tools shown to developers; Fleet shown to agent owners |
| `src/pages/DeveloperDashboard.jsx` | **New page** at `/developer`. Shows agent analytics table (ELO, W/D/L, win rate bar), capability list, quick links to Simulate and Agents pages |
| `src/pages/AgentOwnerHub.jsx` | **New page** at `/owner`. Shows live fleet table (queue status, in-game link, match count, webhook URL) |
| `src/App.jsx` | Routes `/developer` and `/owner` added |

---

## 6. Security Notes

- Role enforcement is **server-side**. Frontend nav filtering is UX only — all protected endpoints return `403 Forbidden` when called by the wrong role regardless of UI state.
- Agent script execution is not yet sandboxed beyond file size (1 MB) and extension (`.py` only) restrictions. Execution isolation (e.g. subprocess, container) is a recommended future hardening step.
- Webhook agents call external URLs controlled by the owner. The platform does not validate or restrict what those URLs do; a malicious webhook could exploit the HTTP call. Rate limiting on the webhook dispatcher is recommended for production.
