import { useEffect, useState } from 'react'
import { applyTheme, getStoredTheme, setStoredTheme } from '../lib/theme'

// Ciclo de 3 estados (claro → escuro → sistema) em vez de um switch binário:
// deixa "seguir o sistema" acessível sem exigir uma tela de configurações à parte.
const NEXT = { light: 'dark', dark: 'system', system: 'light' }

const LABELS = {
  light: 'Tema: claro',
  dark: 'Tema: escuro',
  system: 'Tema: automático (sistema)',
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="10" cy="10" r="4" stroke="currentColor" strokeWidth="1.6" />
      <path
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        d="M10 1.8v2M10 16.2v2M18.2 10h-2M3.8 10h-2M15.6 4.4l-1.4 1.4M5.8 14.2l-1.4 1.4M15.6 15.6l-1.4-1.4M5.8 5.8 4.4 4.4"
      />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
        d="M17 11.5A7.2 7.2 0 0 1 8.5 3a7.5 7.5 0 1 0 8.5 8.5Z"
      />
    </svg>
  )
}

function SystemIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <rect x="2" y="4" width="16" height="10.5" rx="1.4" stroke="currentColor" strokeWidth="1.6" />
      <path stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" d="M7 18h6" />
    </svg>
  )
}

const ICONS = { light: SunIcon, dark: MoonIcon, system: SystemIcon }

export default function ThemeToggle({ floating = false }) {
  const [theme, setTheme] = useState(() => getStoredTheme())

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  useEffect(() => {
    if (theme !== 'system') return
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => applyTheme('system')
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [theme])

  const Icon = ICONS[theme]

  return (
    <button
      type="button"
      className={`theme-toggle${floating ? ' theme-toggle--floating' : ''}`}
      onClick={() => {
        setStoredTheme(NEXT[theme])
        setTheme(NEXT[theme])
      }}
      title={LABELS[theme]}
      aria-label={LABELS[theme]}
    >
      <Icon />
    </button>
  )
}
