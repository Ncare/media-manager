"""Settings read/update (runtime TMDB key + language)."""
from fastapi import APIRouter

from app.config import settings as cfg
from app.schemas import SettingsRead, SettingsUpdate

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsRead)
def read_settings():
    return SettingsRead(
        tmdb_configured=bool(cfg.tmdb_api_key),
        tmdb_language=cfg.tmdb_language,
        media_root=str(cfg.media_root),
    )


@router.patch("/settings", response_model=SettingsRead)
def update_settings(payload: SettingsUpdate):
    if payload.tmdb_api_key is not None:
        cfg.tmdb_api_key = payload.tmdb_api_key
    if payload.tmdb_language is not None:
        cfg.tmdb_language = payload.tmdb_language
    return SettingsRead(
        tmdb_configured=bool(cfg.tmdb_api_key),
        tmdb_language=cfg.tmdb_language,
        media_root=str(cfg.media_root),
    )
