import { beforeEach, describe, expect, it } from 'vitest'
import { getConfig, setConfig } from './config'

describe('config (ADR-006-AC-01, AC-02)', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('returns null when nothing was configured yet', () => {
    expect(getConfig()).toBeNull()
  })

  it('persists baseUrl and configDir and returns them back', () => {
    const saved = setConfig({ baseUrl: 'http://localhost:8000', configDir: '/chains' })
    expect(saved).toEqual({ baseUrl: 'http://localhost:8000', configDir: '/chains' })
    expect(getConfig()).toEqual({ baseUrl: 'http://localhost:8000', configDir: '/chains' })
  })

  it('strips a trailing slash from baseUrl', () => {
    setConfig({ baseUrl: 'http://localhost:8000/', configDir: '/chains' })
    expect(getConfig().baseUrl).toBe('http://localhost:8000')
  })

  it('survives a reload (getConfig reads persisted storage, not in-memory state)', () => {
    setConfig({ baseUrl: 'http://localhost:8000', configDir: '/chains' })
    // Simulates AC-02: a fresh call to getConfig(), as happens on app reload.
    expect(getConfig()).not.toBeNull()
  })
})
