"""Media items: movies, tv shows, seasons, episodes."""
from datetime import datetime

from sqlmodel import Field, SQLModel


class _FileBase(SQLModel):
    """Columns shared by file-level media (Movie / Episode)."""

    id: int | None = Field(default=None, primary_key=True)
    library_id: int = Field(foreign_key="library.id", index=True)
    file_path: str  # absolute path inside container
    filename: str
    title: str | None = None
    year: int | None = None
    # detected-from-filename info (guessit)
    parsed_title: str | None = None
    parsed_year: int | None = None
    parsed_season: int | None = None
    parsed_episode: int | None = None
    # technical fields (from guessit filename parsing)
    resolution: str | None = None
    source: str | None = None        # BluRay / WEB-DL / ...
    codec: str | None = None         # x264 / x265 / ...
    audio_codec: str | None = None
    audio_channels: str | None = None
    release_group: str | None = None
    # scrape state
    tmdb_id: int | None = Field(default=None, index=True)
    imdb_id: str | None = None
    original_title: str | None = None
    scraped: bool = Field(default=False, index=True)
    overview: str | None = None
    rating: float | None = None
    votes: int | None = None
    runtime: int | None = None
    certification: str | None = None
    genres: str | None = None  # comma-separated
    studio: str | None = None
    collection: str | None = None
    language: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Movie(_FileBase, table=True):
    __tablename__ = "movie"


class TvShow(SQLModel, table=True):
    __tablename__ = "tvshow"

    id: int | None = Field(default=None, primary_key=True)
    library_id: int = Field(foreign_key="library.id", index=True)
    folder_path: str
    title: str | None = None
    year: int | None = None
    tmdb_id: int | None = Field(default=None, index=True)
    imdb_id: str | None = None
    original_title: str | None = None
    scraped: bool = Field(default=False, index=True)
    overview: str | None = None
    rating: float | None = None
    votes: int | None = None
    runtime: int | None = None
    certification: str | None = None
    genres: str | None = None
    studio: str | None = None
    collection: str | None = None
    language: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    parsed_title: str | None = None
    parsed_year: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Season(SQLModel, table=True):
    __tablename__ = "season"

    id: int | None = Field(default=None, primary_key=True)
    show_id: int = Field(foreign_key="tvshow.id", index=True)
    season_number: int
    title: str | None = None
    year: int | None = None
    tmdb_id: int | None = None
    poster_path: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Episode(_FileBase, table=True):
    __tablename__ = "episode"

    show_id: int = Field(foreign_key="tvshow.id", index=True)
    season_id: int | None = Field(default=None, foreign_key="season.id", index=True)
    season_number: int | None = None
    episode_number: int | None = None
