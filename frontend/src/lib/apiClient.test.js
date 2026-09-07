import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { setConfig } from './config'
import {
  ApiError,
  archiveRun,
  cancelRun,
  createRunFromTemplate,
  getLocalRepos,
  getRunDetail,
  getRuns,
  getWorkflows,
  openStream,
  postInstruction,
  unarchiveRun,
} from './apiClient'

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

beforeEach(() => {
  window.localStorage.clear()
  setConfig({ baseUrl: 'http://localhost:8000', specsBaseUrl: 'https://example.test/docs' })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('apiClient — connection errors', () => {
  it('surfaces a connection ApiError when fetch itself rejects', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    )
    await expect(getRuns()).rejects.toMatchObject({ kind: 'connection' })
  })
})

describe('apiClient — GET /runs and detail', () => {
  it('returns the parsed list from GET /runs', async () => {
    const runs = [{ chain_name: 'hist-005', status: 'completed' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, runs)))
    await expect(getRuns()).resolves.toEqual(runs)
  })

  it('maps a 404 on GET /runs/{chain_name} to a typed http ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(404, { error: { code: 'not_found', message: 'unknown chain_name: x' } }),
      ),
    )
    await expect(getRunDetail('x')).rejects.toMatchObject({
      kind: 'http',
      status: 404,
      code: 'not_found',
    })
  })
})

describe('apiClient — arquivamento (ADR-011)', () => {
  it('GET /runs sem archived não adiciona query string', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, []))
    vi.stubGlobal('fetch', fetchMock)
    await getRuns()
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/runs')
  })

  it('GET /runs?archived=true quando archived: true', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, []))
    vi.stubGlobal('fetch', fetchMock)
    await getRuns({ archived: true })
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/runs?archived=true')
  })

  it('archiveRun chama POST /runs/{chain_name}/arquivar', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, { chain_name: 'hist-005', archived: true }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await expect(archiveRun('hist-005')).resolves.toEqual({
      chain_name: 'hist-005',
      archived: true,
    })
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/runs/hist-005/arquivar')
    expect(options.method).toBe('POST')
  })

  it('unarchiveRun chama POST /runs/{chain_name}/desarquivar', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, { chain_name: 'hist-005', archived: false }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await expect(unarchiveRun('hist-005')).resolves.toEqual({
      chain_name: 'hist-005',
      archived: false,
    })
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/runs/hist-005/desarquivar')
    expect(options.method).toBe('POST')
  })
})

describe('apiClient — GET /workflows, GET /workspace/repos (ADR-007)', () => {
  it('returns the parsed list from GET /workflows', async () => {
    const workflows = [{ id: 'investigar-impacto', label: 'Investigar impacto', params_schema: [] }]
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, workflows))
    vi.stubGlobal('fetch', fetchMock)
    await expect(getWorkflows()).resolves.toEqual(workflows)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/workflows')
  })

  it('returns the parsed list from GET /workspace/repos', async () => {
    const repos = [{ name: 'ai-lup-poc-target-cli', path: '/repos/ai-lup-poc-target-cli' }]
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, repos))
    vi.stubGlobal('fetch', fetchMock)
    await expect(getLocalRepos()).resolves.toEqual(repos)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/workspace/repos')
  })

  it('sends the configured working folder as ?root= (ADR-009-AC-06)', async () => {
    setConfig({
      baseUrl: 'http://localhost:8000',
      specsBaseUrl: 'https://example.test/docs',
      reposRoot: 'C:/dev/local workflow',
    })
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, []))
    vi.stubGlobal('fetch', fetchMock)

    await getLocalRepos()

    expect(fetchMock.mock.calls[0][0]).toBe(
      'http://localhost:8000/workspace/repos?root=C%3A%2Fdev%2Flocal%20workflow',
    )
  })

  it('omits ?root= when no working folder is configured (ADR-009-AC-07)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, []))
    vi.stubGlobal('fetch', fetchMock)

    await getLocalRepos()

    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/workspace/repos')
  })
})

describe('apiClient — POST /runs/from-template (ADR-007)', () => {
  it('posts template_id and params, returns the started chain_name', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(202, { chain_name: 'investigar-impacto--abc123', status: 'started' }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      createRunFromTemplate('investigar-impacto', { repo_path: '/repos/x', prompt: 'oi' }),
    ).resolves.toEqual({ chain_name: 'investigar-impacto--abc123', status: 'started' })

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/runs/from-template')
    expect(JSON.parse(options.body)).toEqual({
      template_id: 'investigar-impacto',
      params: { repo_path: '/repos/x', prompt: 'oi' },
    })
  })

  it('maps 400 invalid_params to a typed error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(400, { error: { code: 'invalid_params', message: 'missing required params' } }),
      ),
    )
    await expect(createRunFromTemplate('investigar-impacto', {})).rejects.toMatchObject({
      kind: 'http',
      status: 400,
      code: 'invalid_params',
    })
  })

  it('maps 404 template_not_found to a typed error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(404, { error: { code: 'template_not_found', message: 'unknown template' } }),
      ),
    )
    await expect(createRunFromTemplate('does-not-exist', {})).rejects.toMatchObject({
      code: 'template_not_found',
    })
  })
})

describe('apiClient — instrucoes/cancelar', () => {
  it('posts a mensagem to /instrucoes', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(202, { status: 'accepted' }))
    vi.stubGlobal('fetch', fetchMock)
    await postInstruction('hist-005', 'pare e responda X')
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/runs/hist-005/instrucoes')
    expect(JSON.parse(options.body)).toEqual({ mensagem: 'pare e responda X' })
  })

  it('maps 409 not_interactable to a typed error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(409, { error: { code: 'not_interactable', message: 'no active step' } }),
      ),
    )
    await expect(postInstruction('hist-005', 'oi')).rejects.toMatchObject({
      code: 'not_interactable',
    })
  })

  it('reflects the cancelled outcome', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, { status: 'cancelled' })))
    await expect(cancelRun('hist-005')).resolves.toEqual({ status: 'cancelled' })
  })
})

describe('apiClient — openStream', () => {
  function streamResponse(lines) {
    const encoder = new TextEncoder()
    let i = 0
    return {
      ok: true,
      status: 200,
      body: {
        getReader() {
          return {
            async read() {
              if (i >= lines.length) return { done: true, value: undefined }
              const chunk = encoder.encode(`data: ${lines[i]}\n\n`)
              i += 1
              return { done: false, value: chunk }
            },
          }
        },
      },
    }
  }

  it('invokes onLine for each SSE frame received', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamResponse(['{"type":"a"}', '{"type":"b"}'])))
    const received = []
    await openStream('hist-005', { onLine: (line) => received.push(line) })
    expect(received).toEqual(['{"type":"a"}', '{"type":"b"}'])
  })

  it('rejects with a typed not_streamable error on 409, without opening a reader', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(409, { error: { code: 'not_streamable', message: 'no active step' } }),
      ),
    )
    await expect(openStream('hist-005', { onLine: () => {} })).rejects.toMatchObject({
      kind: 'http',
      status: 409,
      code: 'not_streamable',
    })
  })
})

describe('ApiError', () => {
  it('is a real Error subclass carrying kind/status/code', () => {
    const err = new ApiError({ kind: 'http', status: 409, code: 'not_found', message: 'x' })
    expect(err).toBeInstanceOf(Error)
    expect(err.message).toBe('x')
  })
})
