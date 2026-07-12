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

    # --- Proxy (for reaching TMDB from a NAS behind GFW) ---
    # Set via the Settings page (runtime) or env var TMDB_PROXY_URL. When
    # tmdb_proxy_enabled is False, httpx uses env vars (HTTP_PROXY/HTTPS_PROXY)
    # if present, otherwise connects directly.
    tmdb_proxy_url: str = ""           # e.g. http://192.168.31.7:7890
    tmdb_proxy_enabled: bool = False

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
