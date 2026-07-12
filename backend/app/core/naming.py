"""Filename token-replacement engine for renames (tinyMediaManager-style).

A template is a path/name string containing tokens in braces, e.g.::

    {title} ({year})/{title} ({year}) [{resolution}]{ext}

Features
--------
1. **Fallback syntax** ``{a;b;c}`` — try tokens left to right; use the first
   non-empty one. Lets a template degrade gracefully when metadata is missing::

       {originalTitle;title}            -> original if present, else title
       {tmdbId;imdbId;title}            -> id if known, else title
       {titleSort;title;originalTitle}

2. **Per-token separator customization** inside fallback via a leading
   ``:sep`` is *not* supported (tinyMediaManager uses a separate dialog for
   multi-value separators). Keep it simple here.

3. **Sanitization** — every value is cleaned of filesystem-unsafe chars and
   the final result is tidied (empty parens/brackets, trailing spaces before
   the extension, path separators normalized to the OS).

4. **Token reference** — see ``TOKEN_REFERENCE`` below; exposed via the API so
   the frontend can render a cheat sheet.

Tokens are supplied as a flat dict ``{"title": "Inception", "year": 2010, ...}``.
Callers build this dict from the media row (see services/renamer.py).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable

# Characters unsafe on most NAS filesystems (ext4/btrfs/NTFS/exFAT).
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# A token group: {name} or {a;b;c} (fallback). Names are word chars + case.
_TOKEN = re.compile(r"\{([a-zA-Z][\w]*(?:;[a-zA-Z][\w]*)*)\}")


def _safe_name(value: Any) -> str:
    """Strip filesystem-unsafe characters and normalize whitespace."""
    if value in (None, ""):
        return ""
    s = str(value)
    # NFC keeps accented letters intact (better than stripping diacritics).
    s = unicodedata.normalize("NFC", s)
    s = _UNSAFE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _pad(n: Any, width: int = 2) -> str:
    if n in (None, ""):
        return ""
    try:
        return str(int(n)).zfill(width)
    except (TypeError, ValueError):
        return ""


def _build_token_dict(ctx: dict[str, Any]) -> dict[str, str]:
    """Normalize a raw context dict into the token names used by templates.

    Accepts both snake_case keys from the DB (title, original_title, ...) and
    the camelCase token names exposed in the template (title, originalTitle).
    """
    raw = {k: v for k, v in ctx.items() if v not in (None, "")}

    def pick(*keys: str) -> str:
        for k in keys:
            if k in raw and raw[k] not in (None, ""):
                return str(raw[k])
        return ""

    season = pick("season", "season_number")
    episode = pick("episode", "episode_number")

    d: dict[str, str] = {
        # --- titles ---
        "title": _safe_name(pick("title", "parsed_title")),
        "originalTitle": _safe_name(pick("original_title", "originalTitle")),
        "titleSort": _safe_name(pick("title_sort", "titleSort", "title", "parsed_title")),
        # --- dates / ids ---
        "year": pick("year", "parsed_year"),
        "tmdbId": pick("tmdb_id", "tmdbId"),
        "imdbId": pick("imdb_id", "imdbId"),
        # --- classification ---
        "rating": pick("rating"),
        "votes": pick("votes"),
        "genres": _safe_name(pick("genres", "genre")),
        "certification": _safe_name(pick("certification", "content_rating")),
        "runtime": pick("runtime"),
        "studio": _safe_name(pick("studio", "production_companies")),
        "collection": _safe_name(pick("collection", "belongs_to_collection")),
        # --- tv-specific ---
        "season": _pad(season),
        "episode": _pad(episode),
        "seasonEpisode": (f"S{_pad(season)}E{_pad(episode)}"
                          if (season or episode) else ""),
        "showTitle": _safe_name(pick("show_title", "showTitle", "title")),
    }

    # resolution: guessit may give screen_size (1080p) or source-derived.
    resolution = pick("resolution", "screen_size")
    d["resolution"] = _safe_name(resolution) or ""
    d["videoResolution"] = d["resolution"]  # alias

    # source / codec / group — technical fields from filename parsing.
    d["source"] = _safe_name(pick("source", "release_group_source"))
    d["codec"] = _safe_name(pick("codec", "video_codec"))
    d["audioCodec"] = _safe_name(pick("audio_codec"))
    d["audioChannels"] = _safe_name(pick("audio_channels"))
    d["group"] = _safe_name(pick("release_group", "group"))

    # extension: keep the dot, e.g. ".mkv". When only a filename is supplied,
    # extract its suffix rather than using the whole name as the extension.
    ext = pick("ext", "extension")
    if not ext:
        fn = pick("filename")
        if fn and "." in fn:
            ext = "." + fn.rsplit(".", 1)[1]
    if ext and "." not in ext:
        ext = "." + ext.lstrip(".")
    d["ext"] = ext

    # language / country
    d["language"] = _safe_name(pick("language", "original_language"))
    d["country"] = _safe_name(pick("country"))

    return d


def _resolve_token(group: str, tokens: dict[str, str]) -> str:
    """Resolve a token group (possibly fallback ``a;b;c``) to its value."""
    names = [n.strip() for n in group.split(";") if n.strip()]
    for name in names:
        # case-insensitive lookup against the token dict
        val = tokens.get(name) or tokens.get(_camel(name)) or tokens.get(_snake(name))
        if val:
            return val
    return ""


def _camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def apply_template(template: str, context: dict[str, Any]) -> str:
    """Apply token substitution (with fallback) + cleanup to a naming template.

    Args:
        template: e.g. ``"{title} ({year})/{originalTitle;title}{ext}"``
        context:  flat dict of available fields (any key naming works).
    """
    tokens = _build_token_dict(context)

    def _sub(m: re.Match) -> str:
        return _resolve_token(m.group(1), tokens)

    out = _TOKEN.sub(_sub, template)

    # Tidy artifacts from missing tokens.
    out = re.sub(r"\(\s*,?\s*\)", "", out)        # empty / lonely-comma parens
    out = re.sub(r"\[\s*,?\s*\]", "", out)        # empty brackets
    out = re.sub(r"\s{2,}", " ", out)             # collapse spaces
    out = re.sub(r"\s+([)\].,])", r"\1", out)     # space before closers
    out = re.sub(r"\s+(\.\w+)$", r"\1", out)      # trailing space before ext
    out = re.sub(r"[ ]*[\\/][ ]*", "/", out)      # spaces around path sep
    # Collapse empty path segments: "a//b" -> "a/b"
    out = re.sub(r"/+", "/", out)
    # Strip leading path separators (never rename into root).
    out = out.lstrip("/").strip(" .-")
    return out


# ---------------------------------------------------------------------------
# Token reference (for the frontend cheat sheet / docs)
# ---------------------------------------------------------------------------
# Each entry: (token, applies to, example, description)
TOKEN_REFERENCE: list[dict[str, str]] = [
    {"token": "title", "for": "通用", "example": "盗梦空间", "desc": "标题(本地化,如中文标题)"},
    {"token": "originalTitle", "for": "通用", "example": "Inception", "desc": "原始标题(原名/英文标题)"},
    {"token": "titleSort", "for": "通用", "example": "盗梦空间", "desc": "排序标题;缺失时回退到 title"},
    {"token": "year", "for": "通用", "example": "2010", "desc": "年份"},
    {"token": "tmdbId", "for": "通用", "example": "27205", "desc": "TMDB ID"},
    {"token": "imdbId", "for": "通用", "example": "tt1375666", "desc": "IMDB ID(刮削后)"},
    {"token": "rating", "for": "通用", "example": "8.366", "desc": "评分"},
    {"token": "votes", "for": "通用", "example": "37180", "desc": "投票数"},
    {"token": "genres", "for": "通用", "example": "动作, 科幻", "desc": "类型(逗号分隔)"},
    {"token": "certification", "for": "通用", "example": "PG-13", "desc": "分级/年龄认证"},
    {"token": "runtime", "for": "通用", "example": "148", "desc": "时长(分钟)"},
    {"token": "studio", "for": "通用", "example": "Warner Bros.", "desc": "制作公司"},
    {"token": "collection", "for": "通用", "example": "Inception Collection", "desc": "所属合集"},
    {"token": "language", "for": "通用", "example": "en", "desc": "语言"},
    {"token": "country", "for": "通用", "example": "US", "desc": "国家"},
    {"token": "resolution", "for": "通用", "example": "1080p", "desc": "分辨率(videoResolution 同义)"},
    {"token": "source", "for": "通用", "example": "BluRay", "desc": "来源(蓝光/WEB-DL 等)"},
    {"token": "codec", "for": "通用", "example": "x264", "desc": "视频编码"},
    {"token": "audioCodec", "for": "通用", "example": "DTS", "desc": "音频编码"},
    {"token": "audioChannels", "for": "通用", "example": "7.1", "desc": "声道"},
    {"token": "group", "for": "通用", "example": "YIFY", "desc": "发布组"},
    {"token": "ext", "for": "通用", "example": ".mkv", "desc": "扩展名(含点)"},
    {"token": "season", "for": "剧集", "example": "01", "desc": "季号(两位补零)"},
    {"token": "episode", "for": "剧集", "example": "02", "desc": "集号(两位补零)"},
    {"token": "seasonEpisode", "for": "剧集", "example": "S01E02", "desc": "季集组合"},
    {"token": "showTitle", "for": "剧集", "example": "绝命毒师", "desc": "剧集名称"},
]


# Default templates (aligned with tinyMediaManager conventions).
DEFAULT_MOVIE_TEMPLATE = "{title} ({year})/{titleSort;originalTitle;title} ({year}) [{resolution};{source}]{ext}"
DEFAULT_TV_SHOW_TEMPLATE = "{showTitle} ({year})"
DEFAULT_TV_EPISODE_TEMPLATE = (
    "{showTitle}/Season {season}/{showTitle} - {seasonEpisode} - {title;originalTitle}{ext}"
)


def preview_template(template: str, context: dict[str, Any]) -> str:
    """Same as apply_template — alias for clarity in the UI layer."""
    return apply_template(template, context)
