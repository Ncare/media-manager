"""Probe video files with ffprobe to read real codec/resolution/etc.

Used as the *primary* source of technical metadata; the filename-based guessit
parsing in scanner.py is the fallback when ffprobe is unavailable or fails.

ffprobe is invoked as a subprocess (no Python binding dependency) and outputs
JSON, which we normalize into the same field names the scanner/renamer expect.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("media_manager.probe")

# Cache the availability check so we only look up the binary once.
_ffprobe_path: str | None | bool | None = None


def available() -> bool:
    """True if ffprobe is installed and callable."""
    global _ffprobe_path
    if _ffprobe_path is None:
        _ffprobe_path = shutil.which("ffprobe") or False
        if _ffprobe_path:
            log.info("ffprobe found at %s", _ffprobe_path)
        else:
            log.warning("ffprobe not found; technical metadata will rely on filename parsing only")
    return bool(_ffprobe_path)


def probe(path: Path) -> dict:
    """Run ffprobe on a file and return normalized technical fields.

    Returns a dict with keys matching what scanner._technical_fields produces:
    resolution, codec, audio_codec, audio_channels, source (None from probe),
    release_group (None from probe). On any failure returns {} so the caller
    can fall back to guessit.
    """
    if not available():
        return {}
    try:
        # -v error: only print errors, not warnings (keeps output clean)
        # -show_streams -show_format: full stream + container info
        # -of json: machine-readable output
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return {}
        data = json.loads(r.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        log.debug("ffprobe failed on %s: %s", path, e)
        return {}

    streams = data.get("streams", [])
    vstream = next((s for s in streams if s.get("codec_type") == "video"), None)
    astream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    out: dict[str, str | None] = {}

    # --- video codec ---
    if vstream:
        out["codec"] = _normalize_video_codec(vstream.get("codec_name", ""))

        # --- resolution: derive from width/height ---
        w = _to_int(vstream.get("width"))
        h = _to_int(vstream.get("height"))
        if w and h:
            out["resolution"] = _guess_resolution(w, h)

    # --- audio ---
    if astream:
        out["audio_codec"] = _normalize_audio_codec(astream.get("codec_name", ""))
        ch = _to_int(astream.get("channels"))
        if ch:
            out["audio_channels"] = _channels_str(ch)

    return {k: v for k, v in out.items() if v}  # drop empties


# ---- normalizers: map ffprobe's raw codec names to the friendly labels that
#      guessit also produces, so values stay consistent across both sources. ----

_VIDEO_CODEC_MAP = {
    "h264": "H.264", "avc": "H.264", "h264_v4l2m2m": "H.264",
    "hevc": "H.265", "h265": "H.265", "av1": "AV1",
    "vp9": "VP9", "vp8": "VP8", "mpeg4": "MPEG-4",
    "mpeg2video": "MPEG-2", "wmv3": "WMV3", "vc1": "VC-1",
}

_AUDIO_CODEC_MAP = {
    "aac": "AAC", "ac3": "Dolby Digital", "eac3": "Dolby Digital Plus",
    "dts": "DTS", "truehd": "Dolby TrueHD", "dts-hd ma": "DTS-HD MA",
    "flac": "FLAC", "mp3": "MP3", "mp2": "MP2", "opus": "Opus",
    "vorbis": "Vorbis", "pcm_s16le": "PCM", "alac": "ALAC",
}


def _normalize_video_codec(name: str) -> str | None:
    return _VIDEO_CODEC_MAP.get(name.lower().strip()) or (name.upper() or None)


def _normalize_audio_codec(name: str) -> str | None:
    return _AUDIO_CODEC_MAP.get(name.lower().strip()) or (name.upper() or None)


def _to_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _guess_resolution(w: int, h: int) -> str:
    """Map pixel height to the standard size label (matches guessit's output)."""
    # Standard tiers by height. SD < 720 < 1080 < 2160.
    if h >= 2160:
        return "2160p"
    if h >= 1080:
        return "1080p"
    if h >= 720:
        return "720p"
    if h >= 576:
        return "576p"
    if h >= 480:
        return "480p"
    return f"{h}p"


def _channels_str(ch: int) -> str:
    """2 → '2.0', 6 → '5.1', 8 → '7.1' (matches guessit's audio_channels)."""
    if ch == 1:
        return "1.0"
    if ch == 2:
        return "2.0"
    if ch == 6:
        return "5.1"
    if ch == 8:
        return "7.1"
    return f"{ch}ch"
