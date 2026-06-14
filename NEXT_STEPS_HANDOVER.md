# Handover / Next Steps — Sprint 2 (Iunie 2026)

Acest document descrie starea curentă a platformei după **Sprint 2** și pașii rămași pentru echipele viitoare.

## Ce a fost implementat în acest sprint

| Task | Status | Fișiere afectate |
|---|---|---|
| Înlocuire chatbot HuggingFace → Claude API | ✅ DONE | `backend/app/services/chatbot.py` |
| Înlocuire PokerBot/MahjongBot HF → Claude API | ✅ DONE | `backend/app/games/bots/hf_pokerbot.py`, `hf_mahjongbot.py` |
| Evals actualizate pentru Claude bots | ✅ DONE | `evals/provider.py`, `evals/promptfooconfig.yaml` |
| Diagrame tehnice dedicate (8 diagrame Mermaid) | ✅ DONE | `DIAGRAMS.md` |
| Indexuri SQL pentru performanță | ✅ DONE | `alembic/versions/f9a2e3c1b4d7_add_performance_indexes.py` |
| Rate limiting webhook (30 req/60s per owner) | ✅ DONE | `backend/app/services/webhook.py` |
| Docker Build în CI/CD pipeline | ✅ DONE | `.github/workflows/ci.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
| Raport AI Usage actualizat | ✅ DONE | `AI_USAGE_REPORT.md` (Secțiunea 8) |

---

## 1. Sandboxing Real pentru Scripturile Developerilor (High Priority)

### Status Curent:
Scripturile Python uploadate de `ai_developer` sunt executate cu restricții minime (doar verificare de dimensiune <1MB și extensie `.py`). Există un `backend/Dockerfile.sandbox` minimal, dar nu este integrat cu flow-ul de execuție.

### Next Step:
- [ ] Integra `backend/Dockerfile.sandbox` în runner-ul de scripturi (în prezent în `backend/app/services/game.py`)
- [ ] Fiecare script uploadat să fie executat într-un container Docker efemer cu:
  - CPU limit: `--cpus=0.5`
  - Memory limit: `--memory=256m`
  - Network disabled: `--network=none`
  - Timeout: 10 secunde
- [ ] Alternativă mai ușoară: `subprocess.run()` cu `resource.setrlimit` pe Linux
- [ ] De re-testat cu `tests/test_api_auth.py` după integrare

---

## 2. Deploy Automat pe Cloud (Medium Priority)

### Status Curent:
Pipeline-ul CI acum include un job `docker-build` care validează că imaginile se construiesc corect. Lipsește pasul de deploy.

### Next Step:
- [ ] Adăugat job `deploy` în `.github/workflows/ci.yml` care rulează doar pe branch-ul `main` (nu pe PR-uri)
- [ ] Opțiuni recomandate:
  - **Render.com**: `render.yaml` config file, suport nativ pentru Docker
  - **Fly.io**: `fly.toml` + `fly deploy` CLI în CI
  - **AWS EC2**: `docker pull && docker compose up -d` via SSH action
- [ ] Setat secretele în GitHub Secrets: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `SECRET_KEY`
- [ ] De actualizat `CORS_ORIGINS` în `.env` cu domeniul de producție

---

## 3. Re-rulare Evals după Upgrade Claude (Validation)

### Status Curent:
Evals-urile (`evals/promptfooconfig.yaml`) au fost actualizate pentru a folosi boturile Claude. Nu au fost re-rulate din cauza lipsei `ANTHROPIC_API_KEY` în CI.

### Next Step:
- [ ] Setat `ANTHROPIC_API_KEY` ca GitHub Secret
- [ ] Adăugat un job `evals` în CI care rulează `npm run eval` din `evals/`
- [ ] Target: **100% PASS rate** pe toate cele 7 teste (chatbot + poker + chess + mahjong)
- [ ] Actualizat asertiile ChessBot (în prezent acceptă orice output non-gol; de înăsprit la UCI format)

---

## 4. Rate Limiting HTTP pentru API (Medium Priority)

### Status Curent:
Rate limiting-ul există **doar pe webhook-uri** (30 req/60s). REST API-ul nu are rate limiting.

### Next Step:
- [ ] Adăugat `slowapi` sau `fastapi-limiter` (Redis-backed) pentru endpoint-urile publice
- [ ] Limite recomandate:
  - `POST /api/auth/login`: 10 req/min per IP (anti brute-force)
  - `POST /api/simulations`: 5 req/min per user (bulk simulation este costisitor)
  - `POST /api/chat`: 30 req/min per user

---

## 5. Frontend Tests (Low Priority)

### Status Curent:
Nu există teste automate pentru frontend. Toate testele sunt backend-only (pytest).

### Next Step:
- [ ] Adăugat Vitest + React Testing Library în `frontend/package.json`
- [ ] Scris teste pentru componentele critice:
  - `ChessBoard.jsx` — render corect al tablei
  - `Login.jsx` / `Register.jsx` — validare form
  - `Leaderboard.jsx` — render date
- [ ] Adăugat job `frontend-test` în CI pipeline

---

## 6. Monitoring și Alerting (Low Priority)

### Status Curent:
Nu există monitoring de producție. Erorile sunt loggate doar în console.

### Next Step:
- [ ] Integrat Sentry (sau similar) pentru error tracking în backend FastAPI
- [ ] Adăugat `structlog` pentru logging structurat JSON
- [ ] Configured alerte Slack/email pentru erori critice (ex. webhook timeout rate >20%)

---

*Pentru documentația completă a infrastructurii existente, consultați `AI_USAGE_REPORT.md`, `DIAGRAMS.md`, și `implementation_plan.md`.*
