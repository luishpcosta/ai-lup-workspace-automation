import { useEffect, useState } from 'react'
import { getLocalRepos } from '../lib/apiClient'

// ADR-007 RF-02: repositórios locais vêm de GET /workspace/repos (config do
// backend, --local-repos-root) — o frontend nunca lê o filesystem diretamente.
export default function RepoPicker({ id, value, onChange }) {
  const [repos, setRepos] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    getLocalRepos()
      .then((data) => {
        if (!cancelled) setRepos(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error) return <p role="alert">Erro ao listar repositórios locais: {error.message}</p>
  if (repos === null) return <p>Carregando repositórios…</p>
  if (repos.length === 0) {
    return <p>Nenhum repositório local configurado no backend (--local-repos-root).</p>
  }

  return (
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)} required>
      <option value="" disabled>
        Selecione um repositório
      </option>
      {repos.map((repo) => (
        <option key={repo.path} value={repo.path}>
          {repo.name}
        </option>
      ))}
    </select>
  )
}
