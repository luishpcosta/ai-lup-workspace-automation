import { afterEach, describe, expect, it, vi } from 'vitest'
import { SpecsError, fetchSpecContent, fetchSpecsIndex } from './specsClient'

function jsonResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}

function textResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, text: async () => body }
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('fetchSpecsIndex (ADR-007 RF-01)', () => {
  it('fetches docs-index.json directly from the configured remote base URL', async () => {
    const index = [{ id: '005-a', title: 'Spec A', contentPath: '/docs/specs/005-a.md' }]
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, index))
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchSpecsIndex('https://example.github.io/doc-repo-example')).resolves.toEqual(
      index,
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'https://example.github.io/doc-repo-example/docs-index.json',
    )
  })

  it('strips a trailing slash from the base URL before joining', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, []))
    vi.stubGlobal('fetch', fetchMock)

    await fetchSpecsIndex('https://example.github.io/doc-repo-example/')

    expect(fetchMock).toHaveBeenCalledWith(
      'https://example.github.io/doc-repo-example/docs-index.json',
    )
  })

  it('throws a SpecsError on a non-2xx response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(404, {})))
    await expect(fetchSpecsIndex('https://example.test')).rejects.toBeInstanceOf(SpecsError)
  })

  it('throws a SpecsError when fetch itself rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(fetchSpecsIndex('https://example.test')).rejects.toBeInstanceOf(SpecsError)
  })
})

describe('fetchSpecContent (ADR-007 RF-01)', () => {
  it('joins the base URL and a leading-slash contentPath', async () => {
    const fetchMock = vi.fn().mockResolvedValue(textResponse(200, '# Spec A'))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      fetchSpecContent('https://example.github.io/doc-repo-example', '/docs/specs/005-a.md'),
    ).resolves.toBe('# Spec A')
    expect(fetchMock).toHaveBeenCalledWith(
      'https://example.github.io/doc-repo-example/docs/specs/005-a.md',
    )
  })
})
