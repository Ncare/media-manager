"""Settings read/update (runtime TMDB key + language)."""
import logging

from fastapi import APIRouter, HTTPException

from app.config import settings as cfg
from app.schemas import SettingsRead, SettingsUpdate
from app.services.tmdb import TMDBClient, TMDBError

logger = logging.getLogger(__name__)
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


@router.get("/settings/test-tmdb")
async def test_tmdb(key: str | None = None):
    """Test that a TMDB API key works by calling TMDB's /configuration endpoint.

    The key is NOT persisted — this lets the user validate a freshly typed key
    before saving. If no key is passed, the currently configured key is tested.
    """
    test_key = key.strip() if key else None
    if not test_key:
        test_key = cfg.tmdb_api_key or None
    if not test_key:
        raise HTTPException(400, "请先输入要测试的 TMDB API Key")
    client = TMDBClient(api_key=test_key)
    try:
        data = await client.test_connection()
    except TMDBError as e:
        return {"ok": False, "message": str(e)}
    except Exception as e:
        logger.exception("TMDB connection test failed unexpectedly")
        return {"ok": False, "message": f"测试失败:{e}"}
    return {
        "ok": True,
        "message": "连接成功,TMDB API Key 有效",
        # A couple of fields from /configuration for the UI to show as proof.
        "images_base_url": data.get("images", {}).get("base_url"),
    }
