const STORAGE_KEY = 'theme'

// 'light' | 'dark' | 'system' — 'system' follows prefers-color-scheme and is
// never written to <html>, only 'light'/'dark' are (see applyTheme).
export function getStoredTheme() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : 'system'
  } catch {
    return 'system'
  }
}

export function setStoredTheme(theme) {
  try {
    if (theme === 'system') {
      window.localStorage.removeItem(STORAGE_KEY)
    } else {
      window.localStorage.setItem(STORAGE_KEY, theme)
    }
  } catch {
    // localStorage indisponível (modo privado, etc.) — segue sem persistir.
  }
}

function resolveTheme(theme) {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme
}

export function applyTheme(theme) {
  const resolved = resolveTheme(theme)
  document.documentElement.dataset.theme = resolved
  document.documentElement.style.colorScheme = resolved
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) {
    meta.setAttribute('content', resolved === 'dark' ? '#140f12' : '#ffffff')
  }
  return resolved
}
