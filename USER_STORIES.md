# User Stories & Backlog

Acest document descrie cerințele funcționale ale platformei de simulare AI, organizate sub formă de **User Stories** Agile și un **Backlog prioritizat**. 

## 1. User Stories (Agile Format)

Am definit 12 User Stories structurate pe bază de Rol (Human Player, AI Developer, Agent Owner, Admin), demonstrând acoperirea completă a funcționalităților platformei.

### 1.1 Human Player (Jucător Uman)
1. **US-01:** Ca *Human Player*, vreau să mă pot înregistra și autentifica pe platformă, astfel încât să îmi pot accesa istoricul meciurilor și ELO-ul.
   - *Acceptance Criteria:* Autentificare pe bază de JWT; parole hash-uite (bcrypt); alias `/api/auth/me`.
2. **US-02:** Ca *Human Player*, vreau să joc meciuri de Șah/Poker/Mahjong împotriva boților AI interni, astfel încât să mă pot antrena fără a aștepta un adversar uman.
   - *Acceptance Criteria:* Lobbies live via WebSocket; motor de joc valid pe server; interfață web reactivă.
3. **US-03:** Ca *Human Player*, vreau să vizualizez Leaderboard-ul global, astfel încât să îmi pot compara rating-ul ELO cu alți jucători sau agenți AI.
   - *Acceptance Criteria:* Pagină de clasament ordonată descrescător după rating; distincție vizuală între oameni și AI.
4. **US-04:** Ca *Human Player*, vreau să folosesc un Chatbot cu AI, astfel încât să pot primi explicații rapide despre regulile jocurilor.
   - *Acceptance Criteria:* Integrare Chatbot accesibilă din navigație; răspunsuri stream-uite.

### 1.2 AI Developer (Dezvoltator de AI)
5. **US-05:** Ca *AI Developer*, vreau să uploadez propriul meu script Python (`.py`), astfel încât să testez comportamentul agentului meu pe platformă.
   - *Acceptance Criteria:* Formular de upload cu limită <1MB; validare de securitate la execuție.
6. **US-06:** Ca *AI Developer*, vreau să rulez "Bulk Simulations" (până la 200 de meciuri consecutive) în background, astfel încât să obțin o metrică statistică precisă pentru win rate.
   - *Acceptance Criteria:* Integrare cu Celery și Redis; returnare format JSON cu metadate statistice.
7. **US-07:** Ca *AI Developer*, vreau să accesez Dashboard-ul "Dev Tools", astfel încât să vizualizez log-urile complete (Request & Response Payloads) pentru deciziile luate de agenții mei.
   - *Acceptance Criteria:* Acces endpoint cu date complete; payload-uri vizibile în interfața UI.

### 1.3 Agent Owner (Proprietar de Agent Webhook)
8. **US-08:** Ca *Agent Owner*, vreau să îmi conectez agentul via Webhook URL, astfel încât platforma să poată trimite `POST requests` către AI-ul meu hostat pe propriile mele servere.
   - *Acceptance Criteria:* Formular înregistrare webhook URL valid; suport pentru timeouts configurabile.
9. **US-09:** Ca *Agent Owner*, vreau să folosesc panoul "Agent Fleet Hub", astfel încât să pot vedea în timp real câți agenți de-ai mei sunt în coada de meciuri sau în joc.
   - *Acceptance Criteria:* Tabela live cu statusul flotei (Idle, Queue, In-Game); opțiuni de pause/resume.
10. **US-10:** Ca *Agent Owner*, vreau să verific deciziile agentului meu în istoric, dar *fără* ca alți jucători să aibă acces la payload-urile request-urilor mele, astfel încât strategia mea să rămână privată.
    - *Acceptance Criteria:* Rutele de decizie returnează payload null dacă cel ce le accesează nu este owner.

### 1.4 Administrator
11. **US-11:** Ca *Admin*, vreau să pot vizualiza și edita rating-ul sau permisiunile oricărui utilizator, astfel încât să pot modera platforma în caz de abuz.
    - *Acceptance Criteria:* Guard-uri `RequireRole(admin)` pe rutele sensibile.
12. **US-12:** Ca *Admin*, vreau să pot suspenda agenții webhook care generează mutări invalide sau depășesc limitele de timeout constant, pentru a proteja event loop-ul serverului.
    - *Acceptance Criteria:* Mecanism de blacklisting/soft-delete pentru agenții toxici.

---

## 2. Product Backlog

Tabelul de mai jos reprezintă prioritizarea tehnică a cerințelor de mai sus pentru ciclul de dezvoltare curent:

| ID | Title / Task | Priority | Status |
|:---|:---|:---:|:---:|
| **BL-01** | Sistem Bază de Date & Auth JWT | P0 (Critical) | DONE |
| **BL-02** | Chess / Poker / Mahjong Engines | P0 (Critical) | DONE |
| **BL-03** | Frontend Vite & React Router | P1 (High) | DONE |
| **BL-04** | Role-based Access Control (Guards) | P1 (High) | DONE |
| **BL-05** | Integrare HuggingFace TinyGPT-2 Bots | P2 (Medium) | DONE |
| **BL-06** | CI/CD (Linting + Pytest Workflow) | P2 (Medium) | DONE |
| **BL-07** | Evals via Promptfoo pentru testarea agenților | P2 (Medium) | DONE |
| **BL-08** | Sistem de Sandboxing pt Execuția Scripturilor | P3 (Low) | TODO |
| **BL-09** | Rate Limiting Webhooks | P3 (Low) | TODO |
| **BL-10** | Migrare Modele la Claude API | P3 (Low) | TODO |
| **BL-11** | Deploy Docker pe infrastructură Cloud | P4 (Optional) | TODO |

*Observație: Ultimile item-uri (BL-08 - BL-11) au fost delegate către un viitor sprint (vezi `NEXT_STEPS_HANDOVER.md`).*
