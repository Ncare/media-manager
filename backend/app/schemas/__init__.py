"""Pydantic request/response schemas (kept separate from ORM models)."""
from datetime import datetime

from pydantic import BaseModel

from app.models.library import LibraryType
from app.models.task import TaskStatus, TaskType


# ---- Library ----
class LibraryCreate(BaseModel):
    name: str
    type: LibraryType = LibraryType.movie
    root_path: str
    scraper_source: str = "tmdb"
    naming_template: str = "{title} ({year})/{titleSort;originalTitle;title} ({year}) [{resolution};{source}]{ext}"
    tv_show_template: str = "{showTitle} ({year})"
    auto_scrape: bool = True


class LibraryUpdate(BaseModel):
    name: str | None = None
    root_path: str | None = None
    naming_template: str | None = None
    tv_show_template: str | None = None
    auto_scrape: bool | None = None


class LibraryRead(BaseModel):
    id: int
    name: str
    type: LibraryType
    root_path: str
    scraper_source: str
    naming_template: str
    tv_show_template: str
    auto_scrape: bool
    created_at: datetime
    updated_at: datetime
    movie_count: int = 0
    tv_count: int = 0


# ---- Media reads ----
class MovieRead(BaseModel):
    id: int
    library_id: int
    file_path: str
    filename: str
    title: str | None
    year: int | None
    parsed_title: str | None = None
    parsed_year: int | None = None
    tmdb_id: int | None
    imdb_id: str | None = None
    original_title: str | None = None
    scraped: bool
    overview: str | None
    rating: float | None
    votes: int | None = None
    runtime: int | None = None
    certification: str | None = None
    genres: str | None
    studio: str | None = None
    collection: str | None = None
    language: str | None = None
    poster_path: str | None
    backdrop_path: str | None
    # technical (from filename)
    resolution: str | None = None
    source: str | None = None
    codec: str | None = None
    audio_codec: str | None = None
    audio_channels: str | None = None
    release_group: str | None = None


class EpisodeRead(BaseModel):
    id: int
    show_id: int
    season_id: int | None
    season_number: int | None
    episode_number: int | None
    file_path: str
    filename: str
    title: str | None
    tmdb_id: int | None
    imdb_id: str | None = None
    scraped: bool
    overview: str | None
    poster_path: str | None
    resolution: str | None = None
    source: str | None = None
    codec: str | None = None


class TvShowRead(BaseModel):
    id: int
    library_id: int
    folder_path: str
    title: str | None
    year: int | None
    parsed_title: str | None = None
    parsed_year: int | None = None
    tmdb_id: int | None
    imdb_id: str | None = None
    original_title: str | None = None
    scraped: bool
    overview: str | None
    rating: float | None
    votes: int | None = None
    runtime: int | None = None
    certification: str | None = None
    genres: str | None
    studio: str | None = None
    collection: str | None = None
    language: str | None = None
    poster_path: str | None
    backdrop_path: str | None
    season_count: int = 0
    episode_count: int = 0


# ---- Scrape ----
class TmdbSearchResult(BaseModel):
    tmdb_id: int
    title: str
    original_title: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None


class ManualMatch(BaseModel):
    media_type: str  # movie | tv | episode
    media_id: int
    tmdb_id: int
    season_number: int | None = None  # for tv/episode


# ---- Rename ----
class RenamePreviewItem(BaseModel):
    media_id: int
    media_type: str
    from_path: str
    to_path: str
    conflict: bool = False
    reason: str | None = None


class RenamePreview(BaseModel):
    items: list[RenamePreviewItem]


class RenameExecute(BaseModel):
    library_id: int
    items: list[int]  # media_ids selected by the user (from the preview)
    media_type: str = "movie"
    template: str | None = None  # optional override; defaults to library template


class RenameUndo(BaseModel):
    batch_id: str | None = None  # if None, undo latest batch


# ---- Tasks ----
class TaskRead(BaseModel):
    id: int
    library_id: int | None
    type: TaskType
    status: TaskStatus
    total: int
    done: int
    message: str | None
    created_at: datetime
    updated_at: datetime


# ---- Settings ----
class SettingsRead(BaseModel):
    tmdb_configured: bool
    tmdb_language: str
    media_root: str


class SettingsUpdate(BaseModel):
    tmdb_api_key: str | None = None
    tmdb_language: str | None = None
