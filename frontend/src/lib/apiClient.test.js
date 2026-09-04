import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { setConfig } from './config'
import { ApiError, cancelRun, createRun, getRunDetail, getRuns, openStream, postInstruction } from './apiClient'

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

beforeEach(() => {
  window.localStorage.clear()
  setConfig({ baseUrl: 'http://localhost:8000', configDir: '/chains' })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('apiClient — connection errors (ADR-006-AC-03)', () => {
  it('surfaces a connection ApiError when fetch itself rejects', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    )
    await expect(getRuns()).rejects.toMatchObject({ kind: 'connection' })
  })
})

describe('apiClient — GET /runs and detail (ADR-006-AC-04, AC-05)', () => {
  it('returns the parsed list from GET /runs', async () => {
    const runs = [{ chain_name: 'hist-005', status: 'completed' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, runs)))
    await expect(getRuns()).resolves.toEqual(runs)
  })

  it('maps a 404 on GET /runs/{chain_name} to a typed http ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(404, { error: { code: 'not_found', message: "unknown chain_name: x" } }),
      ),
    )
    await expect(getRunDetail('x')).rejects.toMatchObject({
      kind: 'http',
      status: 404,
      code: 'not_found',
    })
  })
})

describe('apiClient — POST /runs (ADR-006-AC-06, AC-13)', () => {
  it('posts config_path and returns the started chain_name', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(202, { chain_name: 'hist-005', status: 'started' }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await expect(createRun('/chains/HIST-005.yaml')).resolves.toEqual({
      chain_name: 'hist-005',
      status: 'started',
    })
    const [, options] = fetchMock.mock.calls[0]
    expect(JSON.parse(options.body)).toEqual({ config_path: '/chains/HIST-005.yaml' })
  })

  it('maps 400 invalid_config to a typed error (one bad id in a batch)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(400, { error: { code: 'invalid_config', message: 'invalid config' } }),
      ),
    )
    await expect(createRun('/chains/DOES-NOT-EXIST.yaml')).rejects.toMatchObject({
      kind: 'http',
      status: 400,
      code: 'invalid_config',
    })
  })
})

describe('apiClient — instrucoes/cancelar (ADR-006-AC-09, AC-10)', () => {
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

describe('apiClient — openStream (ADR-006-AC-07, AC-08)', () => {
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
