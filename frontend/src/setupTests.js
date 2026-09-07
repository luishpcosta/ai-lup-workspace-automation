import '@testing-library/jest-dom/vitest'

// jsdom não implementa matchMedia; ThemeToggle usa para resolver o tema 'system'.
if (!window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })
}
