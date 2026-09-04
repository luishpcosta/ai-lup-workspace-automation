// Configuração do painel (ADR-006 RF-01): URL base do backend + diretório-base
// usado para resolver ID de documento de referência -> config_path (ver
// resolveConfigPath.js). Persistida só em localStorage — nunca hardcoded, nunca
// enviada a nenhum backend (constitution.md, princípio 6).
const STORAGE_KEY = 'painel-config'

export function getConfig() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed.baseUrl || !parsed.configDir) return null
    return parsed
  } catch {
    return null
  }
}

export function setConfig({ baseUrl, configDir }) {
  const value = { baseUrl: baseUrl.trim().replace(/\/+$/, ''), configDir: configDir.trim() }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  return value
}
