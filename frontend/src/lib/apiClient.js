import { getConfig } from './config'

// Erro tipado (ADR-006 plan.md, Architecture & Components): toda tela decide a
// mensagem exibida a partir de `kind`/`status`/`code`, nunca deixa uma chamada
// falhar silenciosamente ou travar a tela esperando (NFR-3).
export class ApiError extends Error {
  constructor({ kind, status, code, message }) {
    super(message)
    this.kind = kind // 'connection' | 'http'
    this.status = status
    this.code = code
  }
}

function requireConfig() {
  const config = getConfig()
  if (!config) {
    throw new ApiError({ kind: 'connection', message: 'Backend não configurado.' })
  }
  return config
}

async function parseErrorBody(response) {
  try {
    const body = await response.json()
    return { code: body?.error?.code, message: body?.error?.message }
  } catch {
    return { code: undefined, message: undefined }
  }
}

async function request(path, options = {}) {
  const { baseUrl } = requireConfig()
  let response
  try {
    response = await fetch(`${baseUrl}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch (err) {
    throw new ApiError({
      kind: 'connection',
      message: `Não foi possível conectar ao backend (${baseUrl}): ${err.message}`,
    })
  }
  if (!response.ok) {
    const { code, message } = await parseErrorBody(response)
    throw new ApiError({
      kind: 'http',
      status: response.status,
      code,
      message: message || `Erro HTTP ${response.status}`,
    })
  }
  if (response.status === 204) return null
  return response.json()
}

export function getRuns() {
  return request('/runs')
}

export function getRunDetail(chainName) {
  return request(`/runs/${encodeURIComponent(chainName)}`)
}

export function createRun(configPath) {
  return request('/runs', { method: 'POST', body: JSON.stringify({ config_path: configPath }) })
}

export function postInstruction(chainName, mensagem) {
  return request(`/runs/${encodeURIComponent(chainName)}/instrucoes`, {
    method: 'POST',
    body: JSON.stringify({ mensagem }),
  })
}

export function cancelRun(chainName) {
  return request(`/runs/${encodeURIComponent(chainName)}/cancelar`, { method: 'POST' })
}

// Stream ao vivo (ADR-005/RF-04): usa fetch + ReadableStream, não EventSource, porque
// o código precisa distinguir 409 (not_streamable) de 200 com corpo SSE — EventSource
// não expõe o status HTTP da conexão inicial de forma utilizável (plan.md, Key
// Decisions). Sem retry automático: uma falha/fim de stream é reportada uma vez via
// onLine/erro lançado, e quem chama decide se tenta de novo (AC-08).
export async function openStream(chainName, { onLine, signal }) {
  const { baseUrl } = requireConfig()
  let response
  try {
    response = await fetch(`${baseUrl}/runs/${encodeURIComponent(chainName)}/stream`, { signal })
  } catch (err) {
    if (err.name === 'AbortError') return
    throw new ApiError({
      kind: 'connection',
      message: `Não foi possível conectar ao backend (${baseUrl}): ${err.message}`,
    })
  }
  if (!response.ok) {
    const { code, message } = await parseErrorBody(response)
    throw new ApiError({
      kind: 'http',
      status: response.status,
      code,
      message: message || `Erro HTTP ${response.status}`,
    })
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let sepIndex = buffer.indexOf('\n\n')
      while (sepIndex !== -1) {
        const frame = buffer.slice(0, sepIndex)
        buffer = buffer.slice(sepIndex + 2)
        onLine(frame.startsWith('data: ') ? frame.slice(6) : frame)
        sepIndex = buffer.indexOf('\n\n')
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') return
    throw err
  }
}
