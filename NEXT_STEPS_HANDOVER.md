# Handover / Next Steps

Acest document este destinat viitorilor developeri (sau următoarei echipe) care vor prelua proiectul. El detaliază aspectele curente ale platformei care necesită implementare, rafinare sau optimizare, continuând munca depusă până la acest punct.

## 1. Înlocuirea modelelor de AI (Urgent)
### Status Curent:
Roboții interni (Chatbot, PokerBot, ChessBot, MahjongBot) folosesc modele HuggingFace foarte mici (ex. `sshleifer/tiny-gpt2`, `SmolLM2-360M`) rulate local pe CPU. Testele automate (Evals cu Promptfoo) au demonstrat că aceste modele au latențe mari și ratează constant formatele stricte (ex. generează text halucinat în loc de comenzi valide de joc).

### Next Step:
- [ ] De înlocuit funcțiile `pick_hf_*_move` din `app/games/bots/` cu apeluri API către modele mai mari (ex: OpenAI `gpt-4o-mini`, Anthropic `claude-3-haiku` sau un server local vLLM / Ollama cu un model de minim 8B parametri).
- [ ] De re-rulat suita `npm run eval` din folderul `evals` după upgrade, pentru a valida că noile modele obțin 100% PASS rate.

## 2. CI/CD: Extindere către Deploy (Medium)
### Status Curent:
Avem GitHub Actions configurate pentru Linting (Frontend) și Testare Automată (Backend Pytest). 

### Next Step:
- [ ] De adăugat pașii de build Docker (`docker build`) în pipeline.
- [ ] De adăugat step de Deploy automat pe un server cloud (ex. AWS EC2, Heroku, Render) dacă testele și evals-urile trec.

## 3. Sandboxing pentru Scripturile Developerilor (High)
### Status Curent:
În prezent, utilizatorii cu rol `ai_developer` pot uploada cod Python pe server. Restricția actuală verifică doar mărimea fișierului (<1MB) și extensia (`.py`).

### Next Step:
- [ ] De implementat un mecanism de sandboxing real pentru execuția scripturilor terțe.
- Soluții recomandate: Utilizarea de containere Docker efemere (gVisor/Firecracker) sau restricționarea prin librării Python (PySandbox / rulare cu resurse limitate).

## 4. Optimizarea Bazei de Date (Low)
### Status Curent:
Pentru baza de date de teste s-a creat `test_platform`. Toate tabelele sunt up-to-date conform `alembic`.

### Next Step:
- [ ] De adăugat indecși SQL mai specifici pentru query-urile frecvente de pe tabelele `matches` și `decision_logs`, mai ales având în vedere că un Developer poate trage date în bulk din ele.

## 5. Webhooks Rate Limiting (Medium)
### Status Curent:
`ai_agent_owner` poate seta webhook-uri către care platforma trimite HTTP POST requests la fiecare turn din joc.

### Next Step:
- [ ] Trebuie introdus un rate limiter și timeout strict per owner, astfel încât o aplicație terță care răspunde lent să nu blocheze event loop-ul platformei (deși folosim `asyncio.to_thread` / async httpx, trebuie prevenite abuzurile de rețea).

---
*Pentru o listă a uneltelor folosite și a infrastructurii deja construite, verificați `AI_USAGE_REPORT.md` și `implementation_plan.md`.*
