# Diagrame Tehnice (UML, Arhitectură, Workflows)

Pentru a asigura un design scalabil și pentru a îndeplini criteriul de diagrame din baremul de dezvoltare software, mai jos sunt prezentate diagramele principale ale arhitecturii sistemului, modelării claselor și fluxurilor de execuție, scrise folosind Mermaid.js.

## 1. System Architecture Diagram

Această diagramă ilustrează comunicarea dintre microserviciile care compun platforma.

```mermaid
flowchart TD
    %% Frontend Layer
    Client[React Frontend / Vite]
    
    %% API Layer
    FastAPI[FastAPI Backend]
    
    %% Async Workers
    Celery[Celery Worker - Bulk Sim]
    
    %% State and Storage
    PostgreSQL[(PostgreSQL 16)]
    Redis[(Redis Pub/Sub & Cache)]
    
    %% External Integrations
    ExternalBot[External Webhook Agent]
    HFModel[HuggingFace Local Model]
    
    %% Edges
    Client -- "REST API (HTTPS)" --> FastAPI
    Client -- "WebSocket (WSS)" --> FastAPI
    
    FastAPI -- "Read/Write Users, Matches, Logs" --> PostgreSQL
    FastAPI -- "Enqueue Tasks" --> Redis
    
    Redis -- "Consume Tasks" --> Celery
    Celery -- "Read/Write Results" --> PostgreSQL
    
    FastAPI -- "In-process inference" --> HFModel
    FastAPI -- "POST state JSON" --> ExternalBot
    Celery -- "In-process inference" --> HFModel
    Celery -- "POST state JSON" --> ExternalBot
```

## 2. UML Diagram - Role Access Control

Această diagramă ilustrează ierarhia entităților (Class Diagram) pentru modelul de baza `User` și permisiunile fiecărui `UserRole`.

```mermaid
classDiagram
    class UserRole {
        <<enumeration>>
        human_player
        ai_developer
        ai_agent_owner
        admin
    }

    class User {
        +UUID id
        +String username
        +String email
        +String password_hash
        +int elo_rating
        +UserRole role
        +register()
        +login()
    }

    class AIAgent {
        +UUID id
        +UUID owner_id
        +String name
        +String webhook_url
        +String ai_type
        +validate_webhook()
    }

    class Match {
        +UUID id
        +String game_type
        +String mode
        +String winner_id
        +int duration
    }

    User --> UserRole : are un
    User "1" *-- "0..*" AIAgent : deține (ai_agent_owner)
    User "1" *-- "0..*" Match : joacă
    AIAgent "1" *-- "0..*" Match : joacă
```

## 3. Workflow Diagram - AI Decision Process

Acest workflow descrie cum decide platforma mutarea unui Agent AI în funcție de rolul acestuia (intern HuggingFace, webhook extern, random).

```mermaid
sequenceDiagram
    participant GM as Game Manager
    participant BotFactory as Bot Resolver
    participant HF as HuggingFace (Local)
    participant WH as Webhook Service (External)

    GM->>BotFactory: get_move(state, agent_type)
    
    alt is 'random'
        BotFactory-->>GM: return random_legal_move()
    else is 'pokerbot' / 'chessbot' / 'mahjongbot'
        BotFactory->>HF: invoke local model (tiny-gpt2)
        HF-->>BotFactory: text prediction
        BotFactory->>BotFactory: parse text to legal move
        BotFactory-->>GM: return validated_move
    else is 'webhook'
        BotFactory->>WH: HTTP POST /webhook (GameState)
        activate WH
        WH-->>BotFactory: JSON {"move": "..."}
        deactivate WH
        BotFactory->>BotFactory: validate returned move
        BotFactory-->>GM: return move
    end
```
