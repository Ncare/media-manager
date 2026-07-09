"""Application configuration loaded from environment / .env."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- TMDB ---
    tmdb_api_key: str = ""
    tmdb_language: str = "zh-CN"
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base: str = "https://image.tmdb.org/t/p"

    # --- Storage ---
    media_root: Path = Path("/media")
    db_path: Path = Path("/data/media_manager.db")

    # --- Permissions (runtime drop-priv handled by entrypoint) ---
    puid: int = 1000
    pgid: int = 1000

    # --- CORS ---
    cors_origins: str = "*"

    @property
    def database_url(self) -> str:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.db_path}"

    @property
    def cors_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
