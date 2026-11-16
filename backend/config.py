from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "AdPilot"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ─── Ollama ───────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_TTL_SECONDS: int = 60 * 60 * 24 * 7     # 7 days

    # Optional read-only MCP integration (not used by campaign planning).
    GOOGLE_ADS_DEVELOPER_TOKEN: str = ""

    # ─── Google Ads MCP — MonitorAgent only (reads via GAQL) ──────────────────
    # MCP server runs as a local subprocess — no URL needed
    # Must be ADC credentials JSON (service account or authorized_user),
    # not an OAuth client_secret JSON downloaded from API credentials page.
    GOOGLE_APPLICATION_CREDENTIALS: str = ""   # /absolute/path/to/adc_credentials.json
    GOOGLE_PROJECT_ID: str = ""                # e.g. adpilot-490718

    # ─── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]  # Vite dev server

    # ─── Helpers ──────────────────────────────────────────────────────────────
    @property
    def google_ads_mcp_env(self) -> dict:
        """Env vars passed to the MCP subprocess launched by MCPTool"""
        return {
            "GOOGLE_APPLICATION_CREDENTIALS": self.GOOGLE_APPLICATION_CREDENTIALS,
            "GOOGLE_PROJECT_ID":              self.GOOGLE_PROJECT_ID,
            "GOOGLE_CLOUD_PROJECT":           self.GOOGLE_PROJECT_ID,
            "GOOGLE_ADS_DEVELOPER_TOKEN":     self.GOOGLE_ADS_DEVELOPER_TOKEN,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()