"""Library model — a managed media folder (movie or tv)."""
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class LibraryType(str, Enum):
    movie = "movie"
    tv = "tv"


class Library(SQLModel, table=True):
    __tablename__ = "library"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: LibraryType = Field(default=LibraryType.movie, index=True)
    root_path: str  # path under MEDIA_ROOT (relative to media_root, or absolute inside container)
    scraper_source: str = "tmdb"  # reserved for future multi-source
    naming_template: str = Field(
        default="{title} ({year})/{title} ({year}){ext}",
        description="Renames apply this template. Tokens: {title} {originalTitle} {year} {tmdbId} "
        "{imdbId} {resolution} {source} {codec} {ext} ... (TV adds {season} {episode} {seasonEpisode}). "
        "Fallback syntax: {originalTitle;title}",
    )
    tv_show_template: str = Field(
        default="{showTitle} ({year})",
        description="Renames the SHOW FOLDER for TV libraries. Tokens: {showTitle} {originalTitle} {year} {tmdbId} ...",
    )
    auto_scrape: bool = Field(default=True, description="Scrape after scan automatically")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
