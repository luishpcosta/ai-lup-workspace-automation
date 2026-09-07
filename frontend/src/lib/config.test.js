import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearConfig,
  getConfig,
  getFieldSources,
  loadDefaults,
  setConfig,
} from './config'

// `defaults` é estado de módulo: sem resetar, o arquivo carregado por um teste
// vazaria para o próximo. Um fetch que falha devolve o módulo ao estado "sem default".
async function resetDefaults() {
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('sem arquivo'))
  await loadDefaults()
  vi.restoreAllMocks()
}

function mockDefaultsFile(body) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    json: async () => body,
  })
}

describe('config (ADR-007)', () => {
  beforeEach(async () => {
    window.localStorage.clear()
    await resetDefaults()
  })

  afterEach(() => {
    vi.restoreAllMocks()
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
      reposRoot: '',
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

describe('config — defaults de boot (ADR-009)', () => {
  beforeEach(async () => {
    window.localStorage.clear()
    await resetDefaults()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('boots configured from painel-config.json when localStorage is empty (AC-01)', async () => {
    mockDefaultsFile({
      baseUrl: 'http://localhost:8000',
      specsBaseUrl: 'https://example.test/specs',
    })
    await loadDefaults()

    expect(getConfig()).toEqual({
      baseUrl: 'http://localhost:8000',
      specsBaseUrl: 'https://example.test/specs',
      reposRoot: '',
    })
  })

  it('lets a saved value win over the file default, field by field (AC-02)', async () => {
    mockDefaultsFile({
      baseUrl: 'http://default:8000',
      specsBaseUrl: 'https://default.test/specs',
    })
    await loadDefaults()
    setConfig({ baseUrl: 'http://escolhido:9000', specsBaseUrl: '' })

    const config = getConfig()
    expect(config.baseUrl).toBe('http://escolhido:9000')
    // O campo deixado vazio continua caindo no default do arquivo.
    expect(config.specsBaseUrl).toBe('https://default.test/specs')
  })

  it('falls back to the settings screen when the file is absent (AC-03)', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('404'))
    await expect(loadDefaults()).resolves.toBeDefined()
    expect(getConfig()).toBeNull()
  })

  it('falls back to the settings screen when the file is invalid JSON (AC-03)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => {
        throw new SyntaxError('Unexpected token')
      },
    })
    await loadDefaults()
    expect(getConfig()).toBeNull()
  })

  it('reports whether each field came from the user or from the file (AC-04)', async () => {
    mockDefaultsFile({
      baseUrl: 'http://default:8000',
      specsBaseUrl: 'https://default.test/specs',
    })
    await loadDefaults()
    setConfig({ baseUrl: 'http://escolhido:9000', specsBaseUrl: '' })

    expect(getFieldSources()).toEqual({
      baseUrl: 'user',
      specsBaseUrl: 'file',
      reposRoot: 'none',
    })
  })

  it('clearConfig discards the saved values and goes back to the file defaults', async () => {
    mockDefaultsFile({
      baseUrl: 'http://default:8000',
      specsBaseUrl: 'https://default.test/specs',
    })
    await loadDefaults()
    setConfig({ baseUrl: 'http://escolhido:9000', specsBaseUrl: 'https://escolhido.test' })

    expect(clearConfig().baseUrl).toBe('http://default:8000')
    expect(getFieldSources().baseUrl).toBe('file')
  })

  it('persists the working folder so it survives a reload (AC-05)', () => {
    setConfig({
      baseUrl: 'http://localhost:8000',
      specsBaseUrl: 'https://example.test',
      reposRoot: 'C:/dev/local-workflow-pipeline',
    })
    expect(getConfig().reposRoot).toBe('C:/dev/local-workflow-pipeline')
  })
})
