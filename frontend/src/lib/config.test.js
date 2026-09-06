import { beforeEach, describe, expect, it } from 'vitest'
import { getConfig, setConfig } from './config'

describe('config (ADR-007)', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('returns null when nothing was configured yet', () => {
    expect(getConfig()).toBeNull()
  })

  it('persists baseUrl and specsBaseUrl and returns them back', () => {
    const saved = setConfig({
      baseUrl: 'http://localhost:8000',
      specsBaseUrl: 'https://example.github.io/doc-repo-example',
    })
    expect(saved).toEqual({
      baseUrl: 'http://localhost:8000',
      specsBaseUrl: 'https://example.github.io/doc-repo-example',
    })
    expect(getConfig()).toEqual(saved)
  })

  it('strips a trailing slash from both baseUrl and specsBaseUrl', () => {
    setConfig({
      baseUrl: 'http://localhost:8000/',
      specsBaseUrl: 'https://example.github.io/doc-repo-example/',
    })
    const config = getConfig()
    expect(config.baseUrl).toBe('http://localhost:8000')
    expect(config.specsBaseUrl).toBe('https://example.github.io/doc-repo-example')
  })

  it('is null when specsBaseUrl is missing (both fields required)', () => {
    window.localStorage.setItem('painel-config', JSON.stringify({ baseUrl: 'http://x' }))
    expect(getConfig()).toBeNull()
  })

  it('survives a reload (getConfig reads persisted storage, not in-memory state)', () => {
    setConfig({ baseUrl: 'http://localhost:8000', specsBaseUrl: 'https://example.test' })
    expect(getConfig()).not.toBeNull()
  })
})
