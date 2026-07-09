"""Settings read/update (runtime TMDB key + language)."""
from fastapi import APIRouter

from app.config import settings as cfg
from app.schemas import SettingsRead, SettingsUpdate

router = APIRouter(tags=["settings"])


def _settings_payload() -> SettingsRead:
    """Build the settings response, including a masked view of the TMDB key
    so the UI can show *which* key is active without exposing it in full."""
    key = cfg.tmdb_api_key or ""
    masked = f"****{key[-4:]}" if len(key) >= 4 else None
    return SettingsRead(
        tmdb_configured=bool(key),
        tmdb_language=cfg.tmdb_language,
        media_root=str(cfg.media_root),
        tmdb_key_masked=masked,
    )


@router.get("/settings", response_model=SettingsRead)
def read_settings():
    return _settings_payload()


@router.patch("/settings", response_model=SettingsRead)
def update_settings(payload: SettingsUpdate):
    if payload.tmdb_api_key is not None:
        cfg.tmdb_api_key = payload.tmdb_api_key
    if payload.tmdb_language is not None:
        cfg.tmdb_language = payload.tmdb_language
    return _settings_payload()
