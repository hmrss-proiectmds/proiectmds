"""
FastAPI application factory.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, chat, games, history, users


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Game Simulation Platform",
        description="Multi-game platform for humans and AI agents",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ──
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(games.router)
    app.include_router(chat.router)
    app.include_router(history.router)

    # ── Health check ──
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()

