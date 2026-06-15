# Raport AI & Implementare Barem (10/10)

Acest document validează îndeplinirea completă a cerințelor pentru evaluarea **"Procesul de dezvoltare software cu AI"**, demonstrând integrarea asistenților bazați pe Inteligență Artificială în toate fazele de dezvoltare ale platformei de Game Simulation.

---

## 0. Agenții AI din Platformă (Ce face fiecare agent)
Platforma integrează multiple tipuri de agenți AI (boți) pentru a permite utilizatorilor să joace meciuri, să testeze strategii sau să învețe regulile jocurilor. Aceștia sunt:

1. **RandomBot (`random`)**:
   - **Ce face**: Acesta este agentul de bază al platformei. Indiferent de joc (Șah, Poker, Mahjong), el calculează lista tuturor mutărilor legale în starea curentă a jocului și alege una aleatoriu (uniform distribuit). 
   - **Rol**: Servește ca baseline (nivel 0 de dificultate) pentru testarea integrării engine-urilor de joc și validarea stabilității tehnice a platformei.
2. **ChessBot (`chessbot`)**:
   - **Ce face**: Un agent care procesează starea tablei de șah în format FEN (Forsyth-Edwards Notation). În varianta curentă (bazată pe modelul HuggingFace `sshleifer/tiny-gpt2`), primește ca input istoricul mutărilor și starea tablei, încearcând să prezică următoarea mutare în format UCI (Universal Chess Interface, ex. `e2e4`). 
   - **Fallback**: Dacă predicția modelului lingvistic este invalidă, trece automat la o strategie fallback de selecție aleatorie.
3. **PokerBot (`pokerbot`)**:
   - **Ce face**: Agent specializat în Texas Hold'em. Evaluează cărțile proprii (`hole cards`), cărțile de pe masă (`community cards`), valoarea pot-ului curent și ce acțiuni s-au luat în runda respectivă. Output-ul este o decizie dintre `FOLD`, `CHECK`, `CALL`, `RAISE <amount>` sau `ALLIN`.
   - **Fallback**: În absența unei predicții coerente, se bazează pe o euristică simplă: șanse mai mari de `CALL/CHECK` (50%), șanse medii de `FOLD` (30%) și șanse mici de `RAISE` (20%).
4. **MahjongBot (`mahjongbot`)**:
   - **Ce face**: Agent pentru Riichi Mahjong. Primește mâna de 14 piese. Modelul LLM este interogat pentru a prezice o acțiune (ex. discard-ul unei piese specifice, declararea de `Tsumo`, `Ron`, `Pon`, `Chi`).
   - **Fallback**: Agentul conține o euristică extrem de sofisticată numită **Shanten Minimizer** (calcularea numărului minim de piese necesare pentru a câștiga mâna, cunoscut ca starea `Tenpai`). Când LLM-ul halucinează, botul calculează matematic piesa optimă pe care s-o arunce astfel încât valoarea `shanten` a mâinii să fie minimizată.
5. **Platform Chatbot (`Chatbot`)**:
   - **Ce face**: Un asistent AI conversațional (LLM integrat în frontend-ul aplicației), separat de mecanica jocurilor. 
   - **Rol**: Răspunde utilizatorilor cu explicații despre regulile jocurilor de Mahjong, Poker și Șah, ajută utilizatorii să înțeleagă scorurile (ELO) și le explică cum funcționează upload-ul de scripturi pentru dezvoltatori.

---

## 1. User Stories & Backlog Creation (2 pct) ✅
*Vezi fișierul separat `USER_STORIES.md` pentru detalii complete.*
- **Generare cu AI:** Am folosit asistentul AI (Google DeepMind Antigravity) pentru a converti cerințele generale de business în **12 User Stories** clare, respectând formatul Agile ("As a [role], I want to [action] so that [benefit]").
- **Backlog Prioritizat:** Tot cu ajutorul AI, am extras un backlog tehnic prioritizat (P0-P4), divizând cerințele complexe în task-uri implementabile: Database Auth, Engines (Chess, Poker, Mahjong), Role-based Guards, etc.
- **Criterii de Acceptanță:** Pentru fiecare US, AI-ul ne-a generat Acceptance Criteria riguroase, facilitând testarea ulterioară.

## 2. Diagrame UML, Arhitectură, Workflows (1 pct) ✅
*Vezi fișierul separat `DIAGRAMS.md`.*
- **Tooling:** Am utilizat AI-ul pentru a genera cod **Mermaid.js** direct din structura codului Python și React, eliminând necesitatea desenării manuale.
- **Acoperire:** Au fost generate automat diagrame pentru arhitectura sistemului (FastAPI + Celery + PostgreSQL), diagrama claselor UML pentru `User` / `AIAgent` / `Role`, și diagrama de Workflow pentru fluxul de luare a deciziilor de către un AI (Local HuggingFace vs Webhook Extern).

## 3. Source Control cu Git (1 pct) ✅
- **Automatizarea cu AI:** Asistentul a preluat sarcina de a rula comenzi Git, rezolvând o situație complexă prin care s-a dat un **Hard Reset** (Rollback) la commit-ul stabil `e90a21de` după ce niște feature-uri experimentale de rate limiting stricaseră pipeline-ul CI.
- **Operațiuni utilizate:** Branch creation (`feature/final-grading-requirements`), commit-uri descriptive generate de LLM, comenzi de manipulare a istoricului (`reset --hard`, `push -f`), simulând un mediu real de versionare asistenată de AI.

## 4. Teste Automate și Evals pentru Agenți (2 pct) ✅
- **Teste Unitare (Pytest):** Asistentul AI a scris și adaptat suita de teste din `tests/test_api_auth.py` și `tests/test_role_guards.py`. AI-ul a identificat rapid probleme de izolare a bazei de date (setup fixtures) și le-a corectat automat.
- **Evals pentru Agenți:** S-a utilizat **Promptfoo** pentru evaluarea boților `sshleifer/tiny-gpt2`. Configurația `evals/promptfooconfig.yaml` a fost generată cu AI pentru a verifica determinist, prin scripturi JavaScript, dacă outputul LLM-ului este o mutare validă (ex. Regex de validare format UCI pentru Șah).

## 5. Raportare Bug și Rezolvare cu Pull Request (1 pct) ✅
- **Bug Raportat:** Pipeline-ul pica din cauza erorii `ValueError: task_id must not be empty` în Celery, atunci când se executau testele în mod "eager" (sincron).
- **Rezolvare AI:** AI-ul a analizat traceback-ul complet citind fișierul `app/tasks/simulations.py`, a dedus că funcția `self.update_state()` nu avea acces la ID-ul cererii (întrucât broker-ul Redis nu era folosit în teste) și a aplicat condiția de siguranță `if getattr(self.request, "id", None)`.
- **Implementare:** Modificarea a fost implementată, s-a generat commit-ul automat și fix-ul a reparat branch-ul principal.

## 6. Pipeline CI/CD (1 pct) ✅
- **Configurare:** Fișierul `.github/workflows/ci.yml` a fost scris integral cu ajutorul inteligenței artificiale.
- **Etape Automatizate:** Pipeline-ul include checkout, testare Python cu dependințe cached, instalare Node.js cu linting ESLint, și mai recent, un job de **Docker Build**.
- **Docker Integration:** AI-ul a generat fișierele `backend/Dockerfile` și `frontend/Dockerfile` și a integrat acțiunea `docker/build-push-action@v5` în CI pentru a garanta că aplicația se construiește corect în cloud.

## 7. Utilizarea AI în timpul Dezvoltării Software (2 pct) ✅
- **Productivitate Maximă:** În loc să se documenteze API-ul SQLAlchemy sau detaliile obscure din React useEffect, asistentul AI a editat direct fișierele, generând cod robust bazat pe bune practici (ex: gestionarea rate-limit-urilor, rezolvarea problemelor de rendering frontend cu `setState`).
- **Debugging Accelerat:** Toate erorile întâlnite în timpul dezvoltării au fost trimise sub formă de log-uri direct către asistent, care a diagnosticat corect problemele de infrastructură (ex: eroarea de conexiune PostgreSQL `role root does not exist` în GitHub Actions a fost rezolvată adăugând argumentul `-U postgres` în comanda de healthcheck generată de AI).
- **Concluzie:** Acest proiect dovedește că un sistem complex (FastAPI, React, Webhooks, Celery, AI Engines) poate fi dezvoltat de un om împreună cu o inteligență artificială, automatizând complet tot ce ține de scrierea testelor, diagramelor și managementului de repo.
