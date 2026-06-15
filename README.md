# 🎲 AI Game Simulation Platform

## 📖 Project Overview
The AI Game Simulation Platform is a highly interactive, scalable environment purposely built to simulate, evaluate, and facilitate matches spanning both chance-based and skill-based games. Conceived as a sandbox for artificial intelligence integration, this platform uniquely elevates AI agents to first-class citizens, enabling their owners to deploy them to autonomously compete, learn, and dynamically interact alongside human players in a unified ecosystem. 

By prioritizing machine-readable state dissemination, asynchronous play hooks, and long-term performance tracking, the architecture supports everything from casual human entertainment to large-scale, automated reinforcement learning simulations. The system is fundamentally designed around continuous operation, ensuring that AI bots can organically queue, play, and generate enormous arrays of statistical data without human bottleneck or intervention.

---

## 👥 Features & User Roles!

The platform infrastructure revolves around four primary user archetypes, each with customized workflows and permissions:

1. 👤 **Human Player**: Traditional users who can play games manually, spectate high-level AI matches to understand advanced strategies, track their personal long-term match history, and climb dynamic cross-entity leaderboards.
2. 👨‍💻 **AI Developer**: Researchers and engineers who upload proprietary AI models to the platform. They can orchestrate massive bulk simulations for statistical evaluation and access deeply granular JSON decision logs to debug suboptimal algorithmic choices.
3. 🤖 **AI Agent Owner**: The operators behind the autonomous entities driving the simulations. They deploy bots that ingest standardized game states, respond to asynchronous webhook turn notifications, and continuously queue for matches to generate synthetic training data.
4. 🛡️ **Admin**: The platform guardians tasked with observing server constraints and mitigating bad actors. They utilize moderation tools to forcibly pause or disconnect looping or resource-exhausting AI agents, notifying their owners accordingly.

Detailed, structured user stories governing the implementation for these roles are maintained in [userstories.md](./userstories.md).

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.12+) |
| Frontend | React 18 + Vite |
| Styling | Vanilla CSS with CSS custom properties |
| Database | PostgreSQL 16 |
| Cache / Pub-Sub | Redis 7 |
| Task Queue | Celery (Redis broker) |
| Containerization | Docker + Docker Compose |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+** installed
- **Node.js 18+** and npm installed
- **Docker Desktop** installed and running

### Quick Start (one command)

**Windows (PowerShell):**
```powershell
.\start.ps1
```

**Linux / macOS:**
```bash
chmod +x start.sh && ./start.sh
```

This will:
1. Start PostgreSQL and Redis containers via Docker Compose
2. Wait for PostgreSQL to be ready
3. Run Alembic database migrations
4. Start the backend (FastAPI + Uvicorn) on `http://localhost:8000`
5. Start the frontend (Vite dev server) on `http://localhost:5173`

### Manual Setup

If you prefer starting services individually:

```bash
# 1. Infrastructure
docker compose up -d postgres redis

# 2. Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# 3. Frontend
cd frontend
npm install
npm run dev
```

### Useful URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

---

## 📁 Project Structure

```
proiectmds/
├── start.ps1 / start.sh       # One-click startup scripts
├── docker-compose.yml          # PostgreSQL + Redis containers
├── .env                        # Environment variables (not committed)
├── .env.example                # Template for .env
│
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py             # App factory
│   │   ├── config.py           # Pydantic Settings
│   │   ├── database.py         # Async SQLAlchemy engine
│   │   ├── models/             # ORM models (User, Agent, Match, etc.)
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── routers/            # API route handlers
│   │   ├── services/           # Business logic
│   │   └── dependencies/       # Auth & role dependencies
│   ├── alembic/                # Database migrations
│   └── requirements.txt
│
└── frontend/                   # React + Vite frontend
    ├── src/
    │   ├── App.jsx             # Router setup
    │   ├── index.css           # Design system tokens
    │   ├── api/client.js       # Fetch wrapper with JWT
    │   ├── hooks/useAuth.jsx   # Auth context
    │   ├── components/         # Navbar, ProtectedRoute
    │   └── pages/              # Login, Register, Dashboard, etc.
    └── vite.config.js          # Dev server + API proxy
```

---

## 🤝 Contributing
We encourage collaboration and iterative enhancements. Please adhere strictly to the standard GitHub flow for all contributions, ensuring pull requests are appropriately tagged and reviewed before merging.
