// ADR-006, Decisão: o que o usuário digita é o ID de um documento de referência,
// não um config_path. A SPA não lê o filesystem local (não tem acesso a ele) — só
// constrói a string do caminho por convenção EXATA (sem glob/fuzzy match).
// Qualquer descompasso de nome vira um erro claro do backend (400 invalid_config),
// não uma resolução automática (ver ADR-006, Consequências).
export function resolveConfigPath(configDir, id) {
  const dir = configDir.trim().replace(/\/+$/, '')
  const trimmedId = id.trim()
  return `${dir}/${trimmedId}.yaml`
}
