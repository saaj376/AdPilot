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
    APP_NAME: str = "AdPilot"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ─── Ollama ───────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_TTL_SECONDS: int = 60 * 60 * 24 * 7     # 7 days

    # ─── Google Ads SDK — LaunchAgent, KeywordAgent, OptimizeAgent (writes) ───
    GOOGLE_ADS_DEVELOPER_TOKEN: str = ""
    GOOGLE_ADS_CLIENT_ID: str = ""
    GOOGLE_ADS_CLIENT_SECRET: str = ""
    GOOGLE_ADS_REFRESH_TOKEN: str = ""
    GOOGLE_ADS_CUSTOMER_ID: str = ""

    # ─── Google Ads MCP — MonitorAgent only (reads via GAQL) ──────────────────
    # MCP server runs as a local subprocess — no URL needed
    # credentials.json = OAuth2 JSON downloaded from Google Cloud Console
    GOOGLE_APPLICATION_CREDENTIALS: str = ""   # /absolute/path/to/credentials.json
    GOOGLE_PROJECT_ID: str = ""                # e.g. albus-490718

    # ─── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]  # Vite dev server

    # ─── Helpers ──────────────────────────────────────────────────────────────
    @property
    def google_ads_sdk_config(self) -> dict:
        """Ready-to-use dict for GoogleAdsClient.load_from_dict()"""
        return {
            "developer_token":   self.GOOGLE_ADS_DEVELOPER_TOKEN,
            "client_id":         self.GOOGLE_ADS_CLIENT_ID,
            "client_secret":     self.GOOGLE_ADS_CLIENT_SECRET,
            "refresh_token":     self.GOOGLE_ADS_REFRESH_TOKEN,
            "login_customer_id": self.GOOGLE_ADS_CUSTOMER_ID,
            "use_proto_plus":    True,
        }

    @property
    def google_ads_mcp_env(self) -> dict:
        """Env vars passed to the MCP subprocess launched by MCPTool"""
        return {
            "GOOGLE_APPLICATION_CREDENTIALS": self.GOOGLE_APPLICATION_CREDENTIALS,
            "GOOGLE_PROJECT_ID":              self.GOOGLE_PROJECT_ID,
            "GOOGLE_ADS_DEVELOPER_TOKEN":     self.GOOGLE_ADS_DEVELOPER_TOKEN,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()