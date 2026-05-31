"""
Application configuration loaded from environment variables.
Uses pydantic-settings so a .env file at the project root is picked up automatically.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gameplatform"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/gameplatform"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth ──
    SECRET_KEY: str = "53e732cef3733dbec57df6cb97277e6bb2cbbfc0eb21e8677fcab5786d452970"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ── App ──
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:5173"

    # ── Email (optional — leave blank to disable email sending) ──
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@gameplatform.local"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
