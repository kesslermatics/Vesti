from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Gemini
    gemini_api_key: str = ""
    # Multimodal-faehiges Gemini 3.5 Modell (per Env ueberschreibbar)
    gemini_model: str = "gemini-3.5-flash-lite"
    # Bildgenerierungs-Modell (Nano Banana) fuer KI-Produktfotos
    gemini_image_model: str = "gemini-3.1-flash-lite-image"

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
