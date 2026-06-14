# Platform Diagrams

This document contains all architectural, UML, and workflow diagrams for the AI Game Simulation Platform.

---

## 1. System Architecture Diagram

High-level overview of all platform components and their communication channels.

```mermaid
graph TB
    subgraph Client ["Client Layer"]
        Browser["Browser (React SPA)"]
        WSClient["WebSocket Client"]
    end

    subgraph Backend ["Backend (FastAPI / Python 3.12)"]
        API["REST API Routers\n(auth, games, agents,\nsimulations, admin,\ndeveloper, owner)"]
        WSServer["WebSocket Server\n(connection manager)"]
        GE["Game Engine Core\n(Chess / Poker / Mahjong)"]
        MM["Matchmaking Service\n(Redis queue)"]
        AGENT["Agent Gateway\n(webhook dispatcher)"]
        BOTS["AI Bots\n(Claude API / ChessBot HF)"]
        ADMIN["Admin Service\n(moderation)"]
        CHAT["Chat Assistant\n(Claude claude-haiku-4-5)"]
    end

    subgraph Data ["Data Layer"]
        PG[("PostgreSQL 16\n(users, matches, agents,\nmatch_moves, decision_logs)")]
        RD[("Redis 7\n(queue, pub/sub, cache)")]
    end

    subgraph Workers ["Background Workers"]
        CEL["Celery Worker\n(bulk simulations)"]
    end

    subgraph External ["External Services"]
        Webhook["AI Agent Webhooks\n(owner-controlled servers)"]
        Claude["Anthropic Claude API\n(haiku-4-5-20251001)"]
    end

    Browser -->|"HTTP / REST"| API
    Browser <-->|"WebSocket"| WSServer
    WSClient <-->|"WebSocket"| WSServer
    API --> GE
    API --> MM
    API --> ADMIN
    API --> CHAT
    WSServer --> GE
    GE --> BOTS
    BOTS -->|"API call"| Claude
    GE --> PG
    GE --> RD
    MM --> RD
    AGENT -->|"HTTP POST"| Webhook
    WSServer -->|"Pub/Sub"| RD
    CEL --> PG
    CEL --> GE
    ADMIN --> PG
    ADMIN --> RD
    CHAT -->|"API call"| Claude
```

---

## 2. Database Entity-Relationship Diagram

Complete relational schema for the platform database.

```mermaid
erDiagram
    users {
        uuid id PK
        string email UK
        string username UK
        string password_hash
        enum role "human_player|ai_developer|ai_agent_owner|admin"
        int elo_rating "default 1200"
        timestamp created_at
    }

    agents {
        uuid id PK
        uuid owner_id FK
        string name
        string game_type
        enum integration_mode "webhook|upload"
        string webhook_url "nullable"
        string script_path "nullable"
        int elo_rating "default 1200"
        bool continuous_queue "default false"
        enum status "active|paused|banned"
        timestamp created_at
    }

    matches {
        uuid id PK
        string game_type
        jsonb final_state
        enum result "player1_win|player2_win|draw"
        enum mode "live|bulk"
        timestamp started_at
        timestamp ended_at
    }

    match_participants {
        uuid id PK
        uuid match_id FK
        uuid player_id FK "nullable"
        uuid agent_id FK "nullable"
        int seat "1 or 2"
        int elo_before
        int elo_after
    }

    match_moves {
        uuid id PK
        uuid match_id FK
        int turn_number
        int seat
        jsonb board_state_before
        jsonb move_payload
        timestamp played_at
    }

    decision_logs {
        uuid id PK
        uuid agent_id FK
        uuid match_id FK
        int turn_number
        jsonb request_payload
        jsonb response_payload
        string exception "nullable"
        timestamp logged_at
    }

    users ||--o{ agents : "owns"
    users ||--o{ match_participants : "plays as"
    agents ||--o{ match_participants : "plays as"
    matches ||--|{ match_participants : "has"
    matches ||--o{ match_moves : "contains"
    agents ||--o{ decision_logs : "generates"
    matches ||--o{ decision_logs : "references"
```

---

## 3. Real-Time WebSocket Sequence Diagram

Shows message flow during a live game between a human player and an AI agent.

```mermaid
sequenceDiagram
    participant H as Human Player (Browser)
    participant WS as WebSocket Server
    participant R as Redis Pub/Sub
    participant GE as Game Engine
    participant AG as Agent Gateway
    participant BOT as AI Agent (Webhook / Claude)

    H->>WS: Connect (JWT auth)
    WS->>R: Subscribe to match:{id}

    note over H,BOT: Human's turn

    H->>WS: send_move("e2e4")
    WS->>GE: validate_move + apply_move
    GE->>R: Publish new state → match:{id}
    R-->>WS: Broadcast
    WS-->>H: Updated board state

    note over H,BOT: Bot's turn

    GE->>AG: it's agent's turn
    AG->>BOT: HTTP POST {game_state, legal_moves}
    BOT-->>AG: {"move": "e7e5"}
    AG->>GE: validate_move + apply_move
    GE->>R: Publish new state → match:{id}
    R-->>WS: Broadcast
    WS-->>H: Updated board state (bot moved)
```

---

## 4. User Role Access Control Diagram (UML Class-like)

Shows which capabilities each role has access to.

```mermaid
classDiagram
    class HumanPlayer {
        +playGames()
        +viewLeaderboard()
        +viewMatchHistory()
        +spectateGames()
        +useChat()
    }

    class AIDeveloper {
        +uploadPythonScript()
        +registerWebhookAgent()
        +runBulkSimulations()
        +viewFullDecisionLogs()
        +downloadLogs()
        +accessDeveloperAnalytics()
    }

    class AgentOwner {
        +registerWebhookAgent()
        +manageAgentQueue()
        +viewFleetHub()
        +viewSummaryLogs()
    }

    class Admin {
        +pauseAgent()
        +banAgent()
        +viewLiveMetrics()
        +accessAllEndpoints()
    }

    HumanPlayer <|-- AIDeveloper : extends
    HumanPlayer <|-- AgentOwner : extends
    AIDeveloper <|-- Admin : extends
    AgentOwner <|-- Admin : extends
```

---

## 5. Matchmaking Workflow

Shows how the Redis-backed matchmaking queue pairs players and starts a game.

```mermaid
flowchart TD
    A([Player / Agent joins queue]) --> B{Queue has compatible opponent?}
    B -- No --> C[Wait in Redis queue\nmax 60s]
    C --> D{Timeout?}
    D -- No --> B
    D -- Yes --> E([Player notified: no match found])
    B -- Yes --> F[Create Match record in PostgreSQL]
    F --> G[Notify both participants]
    G --> H{Participant type?}
    H -- Human --> I[WebSocket: board_state push]
    H -- Agent / Bot --> J[HTTP POST webhook\nor internal bot call]
    I & J --> K([Game begins])
    K --> L{Match ends?}
    L -- Yes --> M[Update ELO ratings]
    M --> N[Save match result to DB]
    N --> O{continuous_queue enabled?}
    O -- Yes --> A
    O -- No --> P([Match complete])
```

---

## 6. AI Bot Decision Flow

Shows how the new Claude-based bots select a move, with fallback chain.

```mermaid
flowchart TD
    Start([Game Engine requests bot move]) --> CheckKey{ANTHROPIC_API_KEY\nconfigured?}
    CheckKey -- No --> Fallback
    CheckKey -- Yes --> BuildPrompt[Build game-state prompt\nwith legal moves list]
    BuildPrompt --> CallClaude[POST to Claude API\nclaude-haiku-4-5-20251001]
    CallClaude --> ParseResponse{Response contains\nvalid legal move?}
    ParseResponse -- Yes --> ReturnMove([Return Claude's chosen move])
    ParseResponse -- No --> Fallback[Weighted-random fallback\nor shanten heuristic]
    Fallback --> ReturnFallback([Return fallback move])
```

---

## 7. CI/CD Pipeline Diagram

Shows the GitHub Actions pipeline triggered on every push/PR to main.

```mermaid
flowchart LR
    Push([git push / PR to main]) --> Parallel

    subgraph Parallel ["Parallel Jobs"]
        BE["Backend Tests\n(Python 3.12 + PostgreSQL)\npytest unit + integration"]
        FE["Frontend Lint\n(Node 20)\nESLint check"]
    end

    FE --> FEBuild["Frontend Build\n(Node 20)\nnpm run build\n+ artifact upload"]

    BE & FEBuild --> Gate{All jobs\npassed?}
    Gate -- Yes --> DockerBuild["Docker Build\n(backend + frontend images)\ndocker build --no-cache"]
    Gate -- No --> Fail([CI FAILED — block merge])
    DockerBuild --> Success([CI PASSED — PR mergeable])
```

---

## 8. Bulk Simulation Sequence Diagram

Shows the Celery-based async pipeline for running headless batch games.

```mermaid
sequenceDiagram
    participant Dev as AI Developer
    participant API as FastAPI
    participant Celery as Celery Worker
    participant GE as Game Engine
    participant DB as PostgreSQL

    Dev->>API: POST /api/simulations\n{agent_id, opponent, game_count}
    API->>Celery: dispatch run_bulk_simulation.delay(...)
    API-->>Dev: 202 Accepted {task_id}

    loop For each game (up to 200)
        Celery->>GE: Run headless game\n(no delays, no WebSocket)
        GE-->>Celery: Result {winner, turns, duration}
        Celery->>DB: Save Match + MatchParticipants
    end

    Celery->>DB: Update agent ELO (bulk)
    Dev->>API: GET /api/simulations/{task_id}
    API-->>Dev: 200 {win_rate, avg_turns, errors, csv_url}
```
