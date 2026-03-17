from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Albus Dumbledore"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ─── Ollama ───────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_TTL_SECONDS: int = 60 * 60 * 24 * 7     # 7 days

    # ─── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]  # Vite dev server


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()