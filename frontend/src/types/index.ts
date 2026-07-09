export type LibraryType = 'movie' | 'tv'
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'canceled'
export type TaskType = 'scan' | 'scrape' | 'rename'

export interface Library {
  id: number
  name: string
  type: LibraryType
  root_path: string
  scraper_source: string
  naming_template: string
  tv_show_template: string
  auto_scrape: boolean
  created_at: string
  updated_at: string
  movie_count?: number
  tv_count?: number
}

export interface Movie {
  id: number
  library_id: number
  file_path: string
  filename: string
  title: string | null
  year: number | null
  parsed_title?: string | null
  parsed_year?: number | null
  tmdb_id: number | null
  scraped: boolean
  overview: string | null
  rating: number | null
  genres: string | null
  poster_path: string | null
  backdrop_path: string | null
  resolution: string | null
}

export interface TvShow {
  id: number
  library_id: number
  folder_path: string
  title: string | null
  year: number | null
  parsed_title?: string | null
  parsed_year?: number | null
  tmdb_id: number | null
  scraped: boolean
  overview: string | null
  rating: number | null
  genres: string | null
  poster_path: string | null
  backdrop_path: string | null
  season_count: number
  episode_count: number
}

export interface Episode {
  id: number
  show_id: number
  season_id: number | null
  season_number: number | null
  episode_number: number | null
  file_path: string
  filename: string
  title: string | null
  tmdb_id: number | null
  scraped: boolean
  overview: string | null
  poster_path: string | null
}

export interface TmdbSearchResult {
  tmdb_id: number
  title: string
  original_title?: string | null
  year?: number | null
  overview?: string | null
  poster_url?: string | null
  backdrop_url?: string | null
}

export interface RenamePreviewItem {
  media_id: number
  media_type: string
  from_path: string
  to_path: string
  conflict: boolean
  reason?: string | null
  // TV-only grouping metadata (undefined for movies)
  show_id?: number | null
  show_title?: string | null
  season_number?: number | null
  to_show_folder?: string | null
  to_season_folder?: string | null
}

export interface RenameToken {
  token: string
  for: string
  example: string
  desc: string
}

export interface Task {
  id: number
  library_id: number | null
  type: TaskType
  status: TaskStatus
  total: number
  done: number
  message: string | null
  created_at: string
  updated_at: string
}

export interface AppSettings {
  tmdb_configured: boolean
  tmdb_language: string
  media_root: string
  tmdb_key_masked: string | null
}
