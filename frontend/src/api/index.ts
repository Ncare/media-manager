import axios from 'axios'
import type {
  AppSettings,
  Episode,
  Library,
  Movie,
  RenamePreviewItem,
  RenameToken,
  Task,
  TmdbSearchResult,
  TvShow,
} from '@/types'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

// ---- Libraries ----
export const librariesApi = {
  list: () => http.get<Library[]>('/libraries').then((r) => r.data),
  create: (data: Partial<Library>) => http.post<Library>('/libraries', data).then((r) => r.data),
  update: (id: number, data: Partial<Library>) =>
    http.patch<Library>(`/libraries/${id}`, data).then((r) => r.data),
  remove: (id: number) => http.delete(`/libraries/${id}`),
  scan: (id: number) => http.post<{ task_id: number; status: string }>(`/libraries/${id}/scan`).then((r) => r.data),
}

// ---- Movies ----
export const moviesApi = {
  list: (params: Record<string, unknown> = {}) =>
    http.get<Movie[]>('/movies', { params }).then((r) => r.data),
  get: (id: number) => http.get<Movie>(`/movies/${id}`).then((r) => r.data),
}

// ---- TV ----
export const tvApi = {
  list: (params: Record<string, unknown> = {}) =>
    http.get<TvShow[]>('/tv', { params }).then((r) => r.data),
  get: (id: number) => http.get<TvShow>(`/tv/${id}`).then((r) => r.data),
  episodes: (showId: number, season: number) =>
    http.get<Episode[]>(`/tv/${showId}/seasons/${season}/episodes`).then((r) => r.data),
}

// ---- Scrape ----
export const scrapeApi = {
  search: (q: string, media_type: string, year?: number) =>
    http.get<TmdbSearchResult[]>('/search', { params: { q, media_type, year } }).then((r) => r.data),
  match: (media_type: string, media_id: number, tmdb_id: number, season_number?: number) =>
    http.post('/match', { media_type, media_id, tmdb_id, season_number }).then((r) => r.data),
}

// ---- Rename ----
export const renameApi = {
  tokens: () => http.get<{ tokens: RenameToken[] }>('/rename/tokens').then((r) => r.data.tokens),
  preview: (libraryId: number, template?: string) =>
    http
      .get<{ items: RenamePreviewItem[] }>(`/rename/preview/${libraryId}`, {
        params: template ? { template } : undefined,
      })
      .then((r) => r.data),
  execute: (library_id: number, items: number[], media_type: string, template?: string) =>
    http.post('/rename/execute', { library_id, items, media_type, template }).then((r) => r.data),
  undo: (batch_id?: string) => http.post('/rename/undo', { batch_id }).then((r) => r.data),
}

// ---- Tasks ----
export const tasksApi = {
  list: () => http.get<Task[]>('/tasks').then((r) => r.data),
  get: (id: number) => http.get<Task>(`/tasks/${id}`).then((r) => r.data),
}

// ---- Settings ----
export const settingsApi = {
  get: () => http.get<AppSettings>('/settings').then((r) => r.data),
  update: (data: Partial<AppSettings>) =>
    http.patch<AppSettings>('/settings', data).then((r) => r.data),
}
