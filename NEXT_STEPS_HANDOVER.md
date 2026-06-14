# Handover / Next Steps — Sprint 3 (Iunie 2026)

Acest document descrie starea curentă a platformei după **Sprint 3** și pașii rămași pentru echipele viitoare.

## Ce a fost implementat în acest sprint

| Task | Status | Fișiere afectate |
|---|---|---|
| Sandbox Docker real pentru scripturi uploadate | ✅ DONE | `backend/sandbox_runner.py`, `backend/Dockerfile.sandbox`, `backend/app/services/game.py` |
| Rate limiting REST API (slowapi) | ✅ DONE | `backend/app/rate_limiter.py`, `app/main.py`, `routers/auth.py`, `routers/chat.py`, `routers/simulations.py` |
| Teste frontend (Vitest + RTL, 13 teste) | ✅ DONE | `frontend/src/test/`, `frontend/package.json`, `frontend/vite.config.js` |
| Evals CI job (Promptfoo) | ✅ DONE | `.github/workflows/ci.yml` |
| Evals: asertie Chess strictă UCI format | ✅ DONE | `evals/promptfooconfig.yaml` |
| Deploy automat Render.com | ✅ DONE | `render.yaml`, `.github/workflows/ci.yml` (deploy job) |

---

## 1. Activarea Deploy-ului Automat (Urgent)

### Status Curent:
`render.yaml` și job-ul `deploy` din CI sunt implementate, dar **nu sunt activate** fără configurare manuală.

### Next Steps:
- [ ] Conecta repo-ul la Render.com: Dashboard → New → Blueprint → selectează repo-ul
- [ ] Seta secretele în Render dashboard: `ANTHROPIC_API_KEY`, `SECRET_KEY`
- [ ] În GitHub → Settings → Variables → Actions, adaugă:
  - `RENDER_DEPLOY_HOOK_URL` = URL-ul hook-ului de deploy din Render dashboard
  - `RUN_EVALS` = `true` (activează job-ul de evals în CI)
- [ ] Adaugă `ANTHROPIC_API_KEY` ca GitHub Secret (pentru job-ul de evals)

---

## 2. Build și Push Docker Images (Medium Priority)

### Status Curent:
CI-ul construiește imaginile Docker (`gameplatform-backend`, `gameplatform-frontend`, `gameplatform-sandbox`) local în runner, dar **nu le publică** nicăieri.

### Next Steps:
- [ ] Adaugă un job `docker-push` în CI care publică imaginile pe **GitHub Container Registry** (ghcr.io) sau **Docker Hub** după ce `ci-passed` trece
- [ ] Configurează secretele: `GHCR_TOKEN` sau `DOCKERHUB_TOKEN`
- [ ] Render.com poate folosi imaginile din registry în loc de build din sursă (mai rapid)
- [ ] Exemplu de pas în CI:
  ```yaml
  - name: Push to GHCR
    uses: docker/build-push-action@v5
    with:
      push: true
      tags: ghcr.io/hmrss-proiectmds/gameplatform-backend:latest
  ```

---

## 3. Construirea Imaginii Sandbox înainte de Utilizare (High Priority)

### Status Curent:
`game.py` apelează `docker run gameplatform-sandbox` dar această imagine trebuie construită **manual** înainte de a porni serverul: `docker build -t gameplatform-sandbox -f backend/Dockerfile.sandbox backend/`.

### Next Steps:
- [ ] Adaugă o comandă de build sandbox în `start.sh` / `start.ps1`:
  ```bash
  docker build -t gameplatform-sandbox -f backend/Dockerfile.sandbox backend/
  ```
- [ ] Sau adaugă un service `sandbox-builder` în `docker-compose.yml` cu `build:` config

---

## 4. Monitorizare și Alerting de Producție (Low Priority)

### Status Curent:
Nu există monitoring de producție. Erorile sunt loggate doar în console.

### Next Steps:
- [ ] Integrat **Sentry** pentru error tracking:
  ```python
  pip install sentry-sdk[fastapi]
  sentry_sdk.init(dsn=settings.SENTRY_DSN)
  ```
- [ ] Adăugat `structlog` pentru logging structurat JSON în producție
- [ ] Configurat alerte pentru: rata de erori >5%, webhook timeout rate >20%

---

## 5. Extindere Teste Frontend (Low Priority)

### Status Curent:
Avem 13 teste în 3 suite-uri (Login, Leaderboard, Navbar). Componentele de joc nu au teste.

### Next Steps:
- [ ] Adaugă teste pentru `ChessBoard.jsx`:
  - Render-ul pieselor pe board
  - Click pe o piesă selectează piesele valide
  - Highlight pe mutarea anterioară
- [ ] Adaugă teste pentru `PokerBoard.jsx`:
  - Render cărților în mână
  - Butoanele de acțiune (FOLD, CALL, RAISE)
- [ ] Target: >50% acoperire pentru componentele din `src/components/`

---

## 6. Rate Limiting Redis-backed (Medium Priority)

### Status Curent:
Rate limiter-ul actual (slowapi) folosește **stocarea în memorie** — nu funcționează corect cu multiple replici/procese.

### Next Steps:
- [ ] Activează backend-ul Redis pentru slowapi:
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address
  limiter = Limiter(key_func=_get_client_ip, storage_uri=settings.REDIS_URL)
  ```
- [ ] Testează cu `pytest` că limita funcționează corect după configurare

---

*Pentru documentația completă, consultați `AI_USAGE_REPORT.md`, `DIAGRAMS.md`, și `implementation_plan.md`.*
