from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenRouter
    openrouter_api_key: str = ""
    # Text-, Vision- und Analysemodell → Env: MODEL
    model: str = "google/gemini-3.8-flash"
    # Bildmodell für Produktbilder und Try-ons → Env: IMAGE_MODEL
    image_model: str = "google/gemini-nano-banana-2.1"

    # Datenbank: lokal SQLite, in Produktion Postgres via DATABASE_URL
    database_url: str = "sqlite:///./vesti.db"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30  # 30 Tage

    # CORS: kommagetrennte Liste erlaubter Origins ("*" fuer alle)
    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
