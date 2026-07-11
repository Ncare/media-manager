import { defineStore } from 'pinia'
import { ref } from 'vue'
import { THEMES, DEFAULT_THEME_ID, getTheme, type ThemePalette } from '@/themes'

const STORAGE_KEY = 'mm.theme.id'

/**
 * Applies a theme by writing its CSS variables onto :root and persisting the id.
 * Element Plus dark mode is toggled so its components track the theme's luminance.
 */
function applyTheme(theme: ThemePalette) {
  const root = document.documentElement
  for (const [key, value] of Object.entries(theme.vars)) {
    root.style.setProperty(key, value)
  }
  // Element Plus has a `.dark` class mode; each theme declares its own
  // luminance so component styling tracks the palette automatically.
  root.classList.toggle('dark', theme.dark)
}

export const useThemeStore = defineStore('theme', () => {
  const currentId = ref<string>(DEFAULT_THEME_ID)
  const current = ref<ThemePalette>(getTheme(DEFAULT_THEME_ID))

  /** Initialize from localStorage (or system preference on first run). */
  function init() {
    let stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) {
      // respect OS preference once, then remember the choice
      const prefersLight =
        window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches
      stored = prefersLight ? 'light' : DEFAULT_THEME_ID
    }
    setTheme(stored)
  }

  function setTheme(id: string) {
    const theme = getTheme(id)
    currentId.value = theme.id
    current.value = theme
    localStorage.setItem(STORAGE_KEY, theme.id)
    applyTheme(theme)
  }

  return {
    currentId,
    current,
    themes: THEMES,
    init,
    setTheme,
  }
})
