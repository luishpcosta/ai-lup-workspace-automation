// Cliente para o repositório remoto de specs (ADR-007 RF-01): fetch DIRETO do
// browser em ${specsBaseUrl}/docs-index.json e, sob demanda, no markdown de cada doc
// via `contentPath` — nunca passa pelo backend do motor (decisão do usuário: o backend
// só recebe os ids já escolhidos, não precisa saber nada sobre esse repositório).
// Formato do índice: mesmo gerado por `doc-repo-example/scripts/generate-docs-index.mjs`
// — [{id, title, contentPath, documentName, root_dir}], contentPath já com "/" inicial.
//
// Separado de apiClient.js de propósito: fala com uma origem HTTP diferente do
// backend do motor (sem `requireConfig()`/tratamento de erro `{error:{code,message}}`
// do motor — este repositório remoto não segue esse contrato).
export class SpecsError extends Error {}

function joinUrl(base, path) {
  const trimmedBase = base.trim().replace(/\/+$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${trimmedBase}${normalizedPath}`
}

async function fetchText(url) {
  let response
  try {
    response = await fetch(url)
  } catch (err) {
    throw new SpecsError(`Não foi possível conectar ao repositório de specs (${url}): ${err.message}`)
  }
  if (!response.ok) {
    throw new SpecsError(`Erro HTTP ${response.status} ao buscar ${url}`)
  }
  return response
}

export async function fetchSpecsIndex(specsBaseUrl) {
  const response = await fetchText(joinUrl(specsBaseUrl, '/docs-index.json'))
  return response.json()
}

export async function fetchSpecContent(specsBaseUrl, contentPath) {
  const response = await fetchText(joinUrl(specsBaseUrl, contentPath))
  return response.text()
}
