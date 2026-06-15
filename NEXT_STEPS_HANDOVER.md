# Handover / Next Steps — Versiunea Finală Stabilă

Acest document reflectă starea de bază a platformei (fără experimente care strică CI-ul) și lasă un set curat de pași pentru echipa viitoare.

## Ce a fost implementat până acum (Core Features)
| Task | Status | Detalii |
|---|---|---|
| User Auth (JWT, Hash) | ✅ DONE | Rutele funcționează perfect; ELO e stocat; `fastapi-users` integration |
| Game Engines | ✅ DONE | Chess, Poker, Mahjong validează mutările corect în memorie |
| Frontend React/Vite | ✅ DONE | Rutare funcțională; tablele de joc pot fi jucate prin WebSockets |
| Evals automate | ✅ DONE | Integrare cu `promptfoo` pentru boții locali HuggingFace (`tiny-gpt2`) |
| Pipeline CI/CD | ✅ DONE | Teste backend, linting frontend, și verificare de **Docker Build** pe GitHub Actions |
| Barem Documentat | ✅ DONE | Diagrame, User Stories, AI Usage Report incluse complet |

---

## Next Steps pentru Viitorii Dezvoltatori

Dacă o altă echipă dorește să continue acest proiect, aici sunt cele 3 mari zone neexplorate încă:

### 1. Sandbox Avansat pentru Scripturile de AI (High Priority)
**Situația curentă:** Dezvoltatorii pot face upload la fișiere Python. Ele sunt rulate în același mediu cu serverul.
**Task:** Fișierele executabile ar trebui izolate sever. Soluții posibile: rularea unui container Docker efemer pentru fiecare script uploadat, sau restricționarea namespace-ului cu librării gen `PySandbox`. 

### 2. Rate Limiting Avansat pentru Webhooks (High Priority)
**Situația curentă:** Platforma este expusă atacurilor de tip DDoS sau spam pe rutele de Webhooks (unde un adversar ar putea invada event loop-ul trimițând requests infinite).
**Task:** Integrarea unui Redis-based rate limiter (ex. `fastapi-limiter`) pentru a limita utilizatorii (`ai_agent_owner`) la maxim 30-50 cereri pe minut pe rutele de Webhooks.

### 3. Înlocuirea modelelor de AI Locale (Medium Priority)
**Situația curentă:** Boții rulează cu `sshleifer/tiny-gpt2`.
**Task:** De integrat un model mai mare sau un API extern (precum Anthropic sau OpenAI) pentru calitatea deciziilor de Șah și Poker.

### 4. Extindere Teste Frontend (Medium Priority)
**Situația curentă:** Testele backend acoperă API-urile și logica de business (`pytest`). Frontend-ul are doar linting și componentele de bază.
**Task:** De integrat un framework precum `Vitest` sau `Jest` + `React Testing Library` pentru a testa rendering-ul componentelor complexe de joc (ex. `ChessBoard.jsx`, `PokerBoard.jsx`).

---
*Proiectul este acum stabil, are 100% test passing rate pe main branch, iar documentația corespunde perfect baremului inițial de dezvoltare.*
