"""Read/write Kodi / Jellyfin / Emby compatible .nfo files (XML)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from app.models.media import Episode, Movie, TvShow

Genres = list[str]


def _add(root: ET.Element, tag: str, value: Any) -> None:
    if value in (None, ""):
        return
    child = ET.SubElement(root, tag)
    child.text = str(value)


def write_movie_nfo(dest: Path, movie: Movie) -> None:
    root = ET.Element("movie")
    _add(root, "title", movie.title)
    _add(root, "originaltitle", movie.parsed_title)
    _add(root, "year", movie.year)
    _add(root, "plot", movie.overview)
    _add(root, "rating", movie.rating)
    _add(root, "uniqueid", movie.tmdb_id)
    for g in (movie.genres or "").split(","):
        g = g.strip()
        if g:
            _add(root, "genre", g)
    _write(dest, root)


def write_tvshow_nfo(dest: Path, show: TvShow) -> None:
    root = ET.Element("tvshow")
    _add(root, "title", show.title)
    _add(root, "originaltitle", show.parsed_title)
    _add(root, "year", show.year)
    _add(root, "plot", show.overview)
    _add(root, "rating", show.rating)
    _add(root, "uniqueid", show.tmdb_id)
    for g in (show.genres or "").split(","):
        g = g.strip()
        if g:
            _add(root, "genre", g)
    _write(dest, root)


def write_episode_nfo(dest: Path, ep: Episode) -> None:
    root = ET.Element("episodedetails")
    _add(root, "title", ep.title)
    _add(root, "season", ep.season_number)
    _add(root, "episode", ep.episode_number)
    _add(root, "plot", ep.overview)
    _add(root, "uniqueid", ep.tmdb_id)
    _write(dest, root)


def _write(dest: Path, root: ET.Element) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(dest, encoding="utf-8", xml_declaration=True)


def read_nfo(path: Path) -> dict:
    """Parse an existing .nfo into a flat dict (for metadata recovery)."""
    data: dict[str, Any] = {}
    if not path.exists():
        return data
    try:
        tree = ET.parse(path)
        for child in tree.getroot():
            tag = child.tag
            text = (child.text or "").strip()
            if tag == "genre":
                data.setdefault("genres", []).append(text)
            elif tag in ("year", "season", "episode", "rating", "uniqueid"):
                if text:
                    try:
                        data[tag] = float(text) if tag == "rating" else int(text)
                    except ValueError:
                        data[tag] = text
            else:
                data[tag] = text
    except ET.ParseError:
        return data
    return data
