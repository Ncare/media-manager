/**
 * Theme palette definitions.
 * Each theme overrides the CSS custom properties declared in style.css :root.
 * `id` is the persisted key; `swatch` is a small preview gradient for the picker.
 */
export interface ThemePalette {
  id: string
  label: string
  /** preview chip background, left=bg → right=accent */
  swatch: string
  vars: Record<string, string>
}

export const THEMES: ThemePalette[] = [
  {
    id: 'dark',
    label: '暗夜',
    swatch: 'linear-gradient(135deg,#1a1d24 0%,#3e8ed0 100%)',
    vars: {
      '--bg': '#0f1115',
      '--panel': '#1a1d24',
      '--panel-2': '#22262f',
      '--text': '#e6e8eb',
      '--muted': '#8b929e',
      '--accent': '#3e8ed0',
      '--accent-2': '#48c78e',
      '--border': '#2c313a',
      '--danger': '#ef4444',
    },
  },
  {
    id: 'light',
    label: '浅色',
    swatch: 'linear-gradient(135deg,#ffffff 0%,#3e8ed0 100%)',
    vars: {
      '--bg': '#f4f6f9',
      '--panel': '#ffffff',
      '--panel-2': '#eef1f6',
      '--text': '#1f2329',
      '--muted': '#6b7280',
      '--accent': '#2563eb',
      '--accent-2': '#10b981',
      '--border': '#e2e6ec',
      '--danger': '#dc2626',
    },
  },
  {
    id: 'oled',
    label: '纯黑',
    swatch: 'linear-gradient(135deg,#000000 0%,#a78bfa 100%)',
    vars: {
      '--bg': '#000000',
      '--panel': '#0a0a0a',
      '--panel-2': '#141414',
      '--text': '#ededed',
      '--muted': '#8a8a8a',
      '--accent': '#a78bfa',
      '--accent-2': '#34d399',
      '--border': '#1f1f1f',
      '--danger': '#f87171',
    },
  },
  {
    id: 'nord',
    label: '极地',
    swatch: 'linear-gradient(135deg,#2e3440 0%,#88c0d0 100%)',
    vars: {
      '--bg': '#2e3440',
      '--panel': '#3b4252',
      '--panel-2': '#434c5e',
      '--text': '#eceff4',
      '--muted': '#81a1c1',
      '--accent': '#88c0d0',
      '--accent-2': '#a3be8c',
      '--border': '#4c566a',
      '--danger': '#bf616a',
    },
  },
]

export const DEFAULT_THEME_ID = 'dark'

export function getTheme(id: string): ThemePalette {
  return THEMES.find((t) => t.id === id) ?? THEMES[0]
}
