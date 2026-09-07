// Configuração do painel: URL base do backend (motor de workflow), URL base do
// repositório remoto de specs (ADR-007 RF-01: `${specsBaseUrl}/docs-index.json` é
// buscado direto do browser, sem passar pelo backend — ver SpecPicker.jsx) e a pasta
// de trabalho (raiz de repositórios, ADR-009 RF-03: vira `?root=` em
// `GET /workspace/repos`).
//
// ADR-009 RF-01: os defaults vêm de `public/painel-config.json`, servido como asset
// estático e lido por `fetch` no boot — não passa pelo bundler, então continua sendo
// configuração de runtime (constitution, princípio 6), editável sem rebuild. A
// precedência é: o que o usuário salvou (localStorage) > default do arquivo > vazio.
const STORAGE_KEY = 'painel-config'
const DEFAULTS_URL = 'painel-config.json'

const EMPTY_DEFAULTS = { baseUrl: '', specsBaseUrl: '', reposRoot: '' }

let defaults = EMPTY_DEFAULTS

function readString(source, key) {
  const value = source?.[key]
  return typeof value === 'string' ? value.trim().replace(/\/+$/, '') : ''
}

// Chamado uma vez no boot (main.jsx) antes do primeiro render, para que `getConfig()`
// continue síncrono em todo o resto do app. Nunca lança: arquivo ausente, JSON
// inválido ou campos faltando degradam para "sem default" (ADR-009-AC-03).
export async function loadDefaults() {
  try {
    const response = await fetch(DEFAULTS_URL, { cache: 'no-store' })
    if (!response.ok) return defaults
    const body = await response.json()
    defaults = {
      baseUrl: readString(body, 'baseUrl'),
      specsBaseUrl: readString(body, 'specsBaseUrl'),
      reposRoot: readString(body, 'reposRoot'),
    }
  } catch {
    defaults = EMPTY_DEFAULTS
  }
  return defaults
}

export function getDefaults() {
  return defaults
}

function readStored() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

// Campo a campo: um valor salvo vazio não "apaga" o default, e um default novo no
// arquivo não sobrescreve o que o usuário escolheu explicitamente (ADR-009-AC-02).
export function getEffectiveConfig() {
  const stored = readStored()
  return {
    baseUrl: readString(stored, 'baseUrl') || defaults.baseUrl,
    specsBaseUrl: readString(stored, 'specsBaseUrl') || defaults.specsBaseUrl,
    reposRoot: readString(stored, 'reposRoot') || defaults.reposRoot,
  }
}

// Diz, por campo, se o valor em vigor veio do usuário ou do arquivo de default —
// é o que a tela de configuração usa para não fingir que um default é digitado
// (ADR-009-AC-04).
export function getFieldSources() {
  const stored = readStored()
  const sourceOf = (key) => (readString(stored, key) ? 'user' : defaults[key] ? 'file' : 'none')
  return {
    baseUrl: sourceOf('baseUrl'),
    specsBaseUrl: sourceOf('specsBaseUrl'),
    reposRoot: sourceOf('reposRoot'),
  }
}

export function getConfig() {
  const config = getEffectiveConfig()
  if (!config.baseUrl || !config.specsBaseUrl) return null
  return config
}

export function setConfig({ baseUrl, specsBaseUrl, reposRoot }) {
  const value = {
    baseUrl: readString({ baseUrl }, 'baseUrl'),
    specsBaseUrl: readString({ specsBaseUrl }, 'specsBaseUrl'),
    reposRoot: readString({ reposRoot }, 'reposRoot'),
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  return value
}

// Volta para os defaults do arquivo (ADR-009-AC-04): descarta o que foi salvo em vez
// de gravar os valores do arquivo por cima, para que uma edição futura do
// painel-config.json volte a valer.
export function clearConfig() {
  window.localStorage.removeItem(STORAGE_KEY)
  return getEffectiveConfig()
}
