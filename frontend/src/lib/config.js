// Configuração do painel: URL base do backend (motor de workflow) + URL base do
// repositório remoto de specs (ADR-007 RF-01: `${specsBaseUrl}/docs-index.json` é
// buscado direto do browser, sem passar pelo backend — ver SpecPicker.jsx). O
// diretório-base de configs (ADR-006) foi removido junto com resolveConfigPath.js:
// o disparo agora é por template (TriggerForm.jsx), não por convenção de nome de
// arquivo. Persistida só em localStorage — nunca hardcoded, nunca enviada a nenhum
// backend (constitution.md, princípio 6).
const STORAGE_KEY = 'painel-config'

export function getConfig() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed.baseUrl || !parsed.specsBaseUrl) return null
    return parsed
  } catch {
    return null
  }
}

export function setConfig({ baseUrl, specsBaseUrl }) {
  const value = {
    baseUrl: baseUrl.trim().replace(/\/+$/, ''),
    specsBaseUrl: specsBaseUrl.trim().replace(/\/+$/, ''),
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  return value
}
