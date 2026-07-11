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
  /** drives Element Plus dark component mode (toggled on <html>) */
  dark: boolean
  vars: Record<string, string>
}

export const THEMES: ThemePalette[] = [
  {
    id: 'dark',
    label: '暗夜',
    dark: true,
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
    dark: false,
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
    dark: true,
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
    dark: true,
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
  {
    id: 'dracula',
    label: '德古拉',
    dark: true,
    swatch: 'linear-gradient(135deg,#282a36 0%,#bd93f9 100%)',
    vars: {
      '--bg': '#282a36',
      '--panel': '#343746',
      '--panel-2': '#44475a',
      '--text': '#f8f8f2',
      '--muted': '#6272a4',
      '--accent': '#bd93f9',
      '--accent-2': '#50fa7b',
      '--border': '#44475a',
      '--danger': '#ff5555',
    },
  },
  {
    id: 'tokyo-night',
    label: '东京之夜',
    dark: true,
    swatch: 'linear-gradient(135deg,#1a1b26 0%,#7aa2f7 100%)',
    vars: {
      '--bg': '#1a1b26',
      '--panel': '#1f2335',
      '--panel-2': '#292e42',
      '--text': '#c0caf5',
      '--muted': '#565f89',
      '--accent': '#7aa2f7',
      '--accent-2': '#9ece6a',
      '--border': '#2a2e42',
      '--danger': '#f7768e',
    },
  },
  {
    id: 'gruvbox',
    label: '复古',
    dark: true,
    swatch: 'linear-gradient(135deg,#282828 0%,#fabd2f 100%)',
    vars: {
      '--bg': '#282828',
      '--panel': '#3c3836',
      '--panel-2': '#504945',
      '--text': '#ebdbb2',
      '--muted': '#928374',
      '--accent': '#fabd2f',
      '--accent-2': '#b8bb26',
      '--border': '#504945',
      '--danger': '#fb4934',
    },
  },
  {
    id: 'solarized-dark',
    label: '日光',
    dark: true,
    swatch: 'linear-gradient(135deg,#002b36 0%,#2aa198 100%)',
    vars: {
      '--bg': '#002b36',
      '--panel': '#073642',
      '--panel-2': '#0d4452',
      '--text': '#93a1a1',
      '--muted': '#586e75',
      '--accent': '#2aa198',
      '--accent-2': '#859900',
      '--border': '#0d4252',
      '--danger': '#dc322f',
    },
  },
  {
    id: 'catppuccin',
    label: '摩卡',
    dark: true,
    swatch: 'linear-gradient(135deg,#1e1e2e 0%,#cba6f7 100%)',
    vars: {
      '--bg': '#1e1e2e',
      '--panel': '#181825',
      '--panel-2': '#313244',
      '--text': '#cdd6f4',
      '--muted': '#7f849c',
      '--accent': '#cba6f7',
      '--accent-2': '#a6e3a1',
      '--border': '#313244',
      '--danger': '#f38ba8',
    },
  },
  {
    id: 'rose-pine',
    label: '蔷薇',
    dark: true,
    swatch: 'linear-gradient(135deg,#191724 0%,#ebbcba 100%)',
    vars: {
      '--bg': '#191724',
      '--panel': '#1f1d2e',
      '--panel-2': '#26233a',
      '--text': '#e0def4',
      '--muted': '#6e6a86',
      '--accent': '#ebbcba',
      '--accent-2': '#9ccfd8',
      '--border': '#2a2740',
      '--danger': '#eb6f92',
    },
  },
]

export const DEFAULT_THEME_ID = 'dark'

export function getTheme(id: string): ThemePalette {
  return THEMES.find((t) => t.id === id) ?? THEMES[0]
}
